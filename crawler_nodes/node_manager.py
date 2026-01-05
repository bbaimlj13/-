#!/usr/bin/env python3
"""
爬虫节点管理器
负责启动、监控和管理Scrapy爬虫节点
支持与API服务器的通信和协调
"""

import os
import sys
import json
import logging
import asyncio
import signal
import time
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional
import redis
import redis.asyncio as redis_async
import psutil
import socket
import uuid

# 添加项目根路径到Python路径，以便导入shared模块
# BASE_DIR 是 /app/crawler_nodes
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# PROJECT_ROOT 是 /app
PROJECT_ROOT = os.path.dirname(BASE_DIR)
sys.path.append(PROJECT_ROOT)

try:
    from shared.config import Config
    from shared.constants import REDIS_KEYS
except ImportError:
    # 兜底：如果shared模块不存在，定义默认配置
    class Config:
        LOG_LEVEL = "INFO"
        # 从环境变量获取Redis密码，默认为'123456'
        REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '123456')
        REDIS_URL = f"redis://:{REDIS_PASSWORD}@redis:6379/0"

        @staticmethod
        def get_redis_url():
            return Config.REDIS_URL

    class REDIS_KEYS:
        NODE_INFO = "node:{node_id}"
        NODE_SET = "nodes"
        SPIDER_NODES = "spider_nodes:{spider_name}"
        SPIDER_STATUS = "spider_status:{spider_name}"
        CHANNEL_NODE_STATUS = "channel:node_status"
        CHANNEL_SPIDER_STATUS = "channel:spider_status"
        CHANNEL_COMMANDS = "channel:commands"
        CHANNEL_RESPONSES = "channel:responses"

# --- 全局日志配置 ---
logger = logging.getLogger(__name__)

class CrawlerNode:
    """爬虫节点类"""

    def __init__(self, node_id: str = None):
        self.node_id = node_id or os.getenv('NODE_ID', f"node_{socket.gethostname()}_{uuid.uuid4().hex[:8]}")
        self.processes: Dict[str, Dict[str, Any]] = {}
        self.spider_status: Dict[str, Dict[str, Any]] = {}
        self.redis_client: redis_async.Redis = None
        self.running = False
        self.start_time = None
        self.base_dir = BASE_DIR
        self.log_dir = os.path.join(BASE_DIR, "logs")

        self.setup_logging()

    def setup_logging(self):
        """配置日志"""
        os.makedirs(self.log_dir, exist_ok=True)

        # 清除已存在的处理器，避免重复添加
        root_logger = logging.getLogger()
        if root_logger.hasHandlers():
            root_logger.handlers.clear()

        logging.basicConfig(
            level=Config.LOG_LEVEL,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(self.log_dir, f'node_{self.node_id}.log'), encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )

    async def initialize(self):
        """初始化节点（带Redis重连逻辑）"""
        max_retry = 3
        retry_count = 0

        while retry_count < max_retry and not self.redis_client:
            try:
                logger.info(f"初始化爬虫节点: {self.node_id}")
                self.redis_client = redis_async.from_url(
                    Config.get_redis_url(),
                    decode_responses=True,
                    max_connections=10,
                    retry_on_timeout=True,
                    socket_timeout=10,
                    socket_connect_timeout=10
                )
                await self.redis_client.ping()
                logger.info("Redis连接成功")

                await self.register_node()
                self.setup_signal_handlers()
                return True

            except redis.exceptions.ConnectionError as e:
                retry_count += 1
                logger.error(f"Redis连接失败（第{retry_count}次重试）: {e}")
                self.redis_client = None
                await asyncio.sleep(2)
            except Exception as e:
                retry_count += 1
                logger.error(f"初始化节点时发生未知错误（第{retry_count}次重试）: {e}", exc_info=True)
                self.redis_client = None
                await asyncio.sleep(2)

        logger.error("Redis连接重试次数耗尽，初始化失败")
        return False

    def setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
        logger.debug("信号处理器已设置")

    def handle_signal(self, signum, frame):
        """处理系统信号"""
        logger.info(f"收到信号 {signum}，开始优雅关闭...")
        self.running = False

    async def register_node(self):
        """注册节点到Redis"""
        try:
            node_info = {
                "id": self.node_id, "hostname": socket.gethostname(),
                "ip": socket.gethostbyname(socket.gethostname()), "pid": os.getpid(),
                "start_time": datetime.now().isoformat(), "status": "starting", "version": "1.0.0"
            }
            node_key = REDIS_KEYS["NODE_INFO"].format(node_id=self.node_id)
            await self.redis_client.set(node_key, json.dumps(node_info), ex=3600)
            await self.redis_client.sadd(REDIS_KEYS["NODE_SET"], self.node_id)

            health_key = f"crawler_node_{self.node_id}"
            await self.redis_client.set(health_key, "online", ex=300)
            logger.info(f"节点健康 Key 注册成功: {health_key}")
            logger.info(f"节点已注册: {self.node_id}")
        except Exception as e:
            logger.error(f"注册节点失败: {e}", exc_info=True)
            raise

    async def renew_node_health_key(self):
        """定时续期健康检查Key"""
        while self.running:
            try:
                if not self.redis_client:
                    logger.warning("Redis客户端未初始化，无法续期健康Key，将在1分钟后重试...")
                    await asyncio.sleep(60)
                    continue

                await self.redis_client.ping()
                health_key = f"crawler_node_{self.node_id}"
                await self.redis_client.set(health_key, "online", ex=300)
                logger.debug(f"节点健康 Key 续期成功: {health_key}")
                await asyncio.sleep(240)
            except redis.exceptions.ConnectionError:
                logger.error("Redis连接已断开，无法续期健康Key，将在1分钟后重试...")
                self.redis_client = None
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"节点健康 Key 续期失败: {e}", exc_info=True)
                await asyncio.sleep(60)

    async def initialize_redis(self):
        """单独初始化Redis（用于重连）"""
        try:
            self.redis_client = redis_async.from_url(
                Config.get_redis_url(),
                decode_responses=True,
                max_connections=10,
                retry_on_timeout=True
            )
            await self.redis_client.ping()
            logger.info("Redis重连成功")
            return True
        except Exception as e:
            logger.error(f"Redis重连失败: {e}")
            self.redis_client = None
            return False

    async def update_node_status(self, status: str = "running", stats: Dict[str, Any] = None):
        """更新节点状态"""
        try:
            if not self.redis_client:
                await self.initialize_redis()
                if not self.redis_client: return

            await self.redis_client.ping()

            node_key = REDIS_KEYS["NODE_INFO"].format(node_id=self.node_id)
            node_info_str = await self.redis_client.get(node_key)
            node_info = json.loads(node_info_str) if node_info_str else {}
            node_info.update({
                "status": status, "last_update": datetime.now().isoformat(),
                "stats": stats or {}, "system": self.get_system_stats()
            })
            await self.redis_client.set(node_key, json.dumps(node_info), ex=3600)
            await self.publish_status_update(status, stats)
        except redis.exceptions.ConnectionError:
            logger.error("Redis连接已断开，无法更新节点状态。")
            self.redis_client = None
        except Exception as e:
            logger.error(f"更新节点状态失败: {e}", exc_info=True)

    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        try:
            process = psutil.Process()
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "process_memory": process.memory_info().rss,
                "process_cpu": process.cpu_percent(interval=0.1),
                "thread_count": process.num_threads(),
                "uptime": time.time() - process.create_time()
            }
        except Exception as e:
            logger.error(f"获取系统统计失败: {e}", exc_info=True)
            return {}

    async def publish_status_update(self, status: str, stats: Dict[str, Any] = None):
        """发布状态更新"""
        try:
            if not self.redis_client:
                await self.initialize_redis()
                if not self.redis_client: return

            await self.redis_client.ping()
            message = {
                "type": "node_status_update", "node_id": self.node_id,
                "status": status, "stats": stats, "timestamp": datetime.now().isoformat()
            }
            await self.redis_client.publish(REDIS_KEYS["CHANNEL_NODE_STATUS"], json.dumps(message))
            logger.debug(f"状态更新已发布: {status}")
        except redis.exceptions.ConnectionError:
            logger.error("Redis连接已断开，无法发布状态更新。")
            self.redis_client = None
        except Exception as e:
            logger.error(f"发布状态更新失败: {e}", exc_info=True)

    async def start_spider(self, spider_name: str, args: List[str] = None) -> bool:
        """启动爬虫 (最终稳定版)"""
        if spider_name in self.processes:
            logger.warning(f"爬虫 {spider_name} 已经在运行")
            return False

        scrapy_project_dir = "/app/scrapy_project"
        if not os.path.exists(scrapy_project_dir):
            logger.error(f"Scrapy项目目录不存在: {scrapy_project_dir}")
            return False

        # 构建基础命令
        cmd = [
            sys.executable,  # 使用当前环境的Python解释器
            "-m", "scrapy",
            "crawl", spider_name,
            "-a", f"redis_url={Config.get_redis_url()}"
        ]
        if args:
            cmd.extend(args)

        spider_log_path = os.path.join(self.log_dir, f"{spider_name}_{self.node_id}.log")
        log_file = open(spider_log_path, "a", encoding="utf-8")

        try:
            # ======================= 关键修改在这里 =======================
            # 不再需要复杂的 shell=True 或 env 字典
            # 只需指定命令、工作目录和日志文件即可
            process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=log_file,
                cwd=scrapy_project_dir,
                # env 参数被移除，子进程会自动继承父进程的 PYTHONPATH
                # shell=True 也被移除，这是更安全、更推荐的做法
            )
            # ============================================================

            self.processes[spider_name] = {
                "process": process, "start_time": datetime.now().isoformat(),
                "pid": process.pid, "log_file": log_file, "log_path": spider_log_path
            }
            self.spider_status[spider_name] = {
                "status": "running", "start_time": datetime.now().isoformat(),
                "pid": process.pid, "node_id": self.node_id, "log_path": spider_log_path
            }
            await self.register_spider(spider_name)
            logger.info(f"爬虫 {spider_name} 已启动，PID: {process.pid}，日志: {spider_log_path}")
            return True
        except Exception as e:
            log_file.close()
            logger.error(f"启动爬虫 {spider_name} 失败: {e}", exc_info=True)
            return False

    async def register_spider(self, spider_name: str):
        """注册爬虫到Redis"""
        try:
            if not self.redis_client:
                await self.initialize_redis()
                if not self.redis_client: return

            await self.redis_client.ping()
            spider_node_key = REDIS_KEYS["SPIDER_NODES"].format(spider_name=spider_name)
            await self.redis_client.sadd(spider_node_key, self.node_id)
            await self.redis_client.set(REDIS_KEYS["SPIDER_STATUS"].format(spider_name=spider_name), "running")
            await self.redis_client.publish(REDIS_KEYS["CHANNEL_SPIDER_STATUS"], json.dumps({
                "type": "spider_started", "spider_name": spider_name, "node_id": self.node_id, "timestamp": datetime.now().isoformat()
            }))
        except redis.exceptions.ConnectionError:
            logger.error("Redis连接已断开，无法注册爬虫。")
            self.redis_client = None
        except Exception as e:
            logger.error(f"注册爬虫失败: {e}", exc_info=True)

    async def stop_spider(self, spider_name: str) -> bool:
        """停止爬虫"""
        if spider_name not in self.processes:
            logger.warning(f"爬虫 {spider_name} 未在运行")
            return False

        process_info = self.processes[spider_name]
        process = process_info["process"]
        log_file = process_info.get("log_file")
        log_path = process_info.get("log_path")

        try:
            if process.poll() is None:
                logger.info(f"停止爬虫 {spider_name}，PID: {process.pid}")
                process.terminate()
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    logger.warning(f"爬虫 {spider_name} 强制终止")
                    process.kill()
                    process.wait()
        finally:
            if log_file and not log_file.closed:
                try:
                    log_file.close()
                except Exception as e:
                    logger.error(f"关闭日志文件失败: {e}")

        del self.processes[spider_name]
        self.spider_status[spider_name] = {
            "status": "stopped", "stop_time": datetime.now().isoformat(), "node_id": self.node_id
        }
        await self.unregister_spider(spider_name)
        logger.info(f"爬虫 {spider_name} 已停止")
        return True

    async def unregister_spider(self, spider_name: str):
        """从Redis中注销爬虫"""
        try:
            if not self.redis_client:
                await self.initialize_redis()
                if not self.redis_client: return

            await self.redis_client.ping()
            spider_node_key = REDIS_KEYS["SPIDER_NODES"].format(spider_name=spider_name)
            await self.redis_client.srem(spider_node_key, self.node_id)
            if await self.redis_client.scard(spider_node_key) == 0:
                await self.redis_client.set(REDIS_KEYS["SPIDER_STATUS"].format(spider_name=spider_name), "stopped")
            await self.redis_client.publish(REDIS_KEYS["CHANNEL_SPIDER_STATUS"], json.dumps({
                "type": "spider_stopped", "spider_name": spider_name, "node_id": self.node_id, "timestamp": datetime.now().isoformat()
            }))
        except redis.exceptions.ConnectionError:
            logger.error("Redis连接已断开，无法注销爬虫。")
            self.redis_client = None
        except Exception as e:
            logger.error(f"注销爬虫失败: {e}", exc_info=True)

    async def check_spider_health(self):
        """检查爬虫健康状态"""
        for spider_name, process_info in list(self.processes.items()):
            process = process_info["process"]
            if process.poll() is not None:
                exit_code = process.returncode
                status = "completed" if exit_code == 0 else "crashed"
                logger.info(f"爬虫 {spider_name} 已退出，状态: {status}，退出码: {exit_code}")

                log_file = process_info.get("log_file")
                if log_file and not log_file.closed:
                    log_file.close()

                del self.processes[spider_name]
                self.spider_status[spider_name] = {
                    "status": status, "exit_code": exit_code,
                    "stop_time": datetime.now().isoformat(), "node_id": self.node_id
                }
                await self.unregister_spider(spider_name)

                if exit_code != 0:
                    logger.info(f"尝试重启异常退出的爬虫: {spider_name}")
                    await self.start_spider(spider_name)

    async def listen_for_commands(self):
        """监听来自Redis的命令（最终稳定版）"""
        pubsub: redis_async.PubSub = None
        logger.info("命令监听器已启动，准备订阅频道...")

        while self.running:
            try:
                if pubsub is None or (pubsub.connection and pubsub.connection.closed):
                    if not self.redis_client:
                        if not await self.initialize_redis():
                            logger.warning("Redis 连接失败，5秒后重试订阅...")
                            await asyncio.sleep(5)
                            continue

                    pubsub = self.redis_client.pubsub()
                    await pubsub.subscribe(**{REDIS_KEYS["CHANNEL_COMMANDS"]: self.handle_command_wrapper})
                    logger.info(f"已成功订阅频道: {REDIS_KEYS['CHANNEL_COMMANDS']}，开始监听命令...")

                async for message in pubsub.listen():
                    pass

            except redis.exceptions.ConnectionError:
                logger.error("与Redis的连接在监听时断开，将在5秒后尝试重连...")
                if pubsub:
                    try:
                        await pubsub.close()
                    except:
                        pass
                pubsub = None
                self.redis_client = None
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"监听命令时发生未知错误: {e}", exc_info=True)
                if pubsub:
                    try:
                        await pubsub.close()
                    except:
                        pass
                pubsub = None
                await asyncio.sleep(5)

        logger.info("命令监听器已停止。")
        if pubsub:
            try:
                await pubsub.close()
            except:
                pass

    async def handle_command_wrapper(self, message):
        """PubSub消息处理包装器"""
        try:
            if message["type"] == "message":
                command = json.loads(message["data"])
                asyncio.create_task(self.handle_command(command))
        except json.JSONDecodeError as e:
            logger.error(f"解析命令失败: {e}，原始消息: {message}")
        except Exception as e:
            logger.error(f"处理消息时发生包装错误: {e}", exc_info=True)

    async def handle_command(self, command: Dict[str, Any]):
        """处理命令"""
        cmd_type = command.get("type")
        logger.info(f"收到命令: {cmd_type}，参数: {command}")

        try:
            if cmd_type == "start_spider":
                spider_name = command.get("spider_name")
                await self.start_spider(spider_name, command.get("args"))
            elif cmd_type == "stop_spider":
                spider_name = command.get("spider_name")
                await self.stop_spider(spider_name)
            elif cmd_type == "restart_spider":
                spider_name = command.get("spider_name")
                await self.stop_spider(spider_name)
                await asyncio.sleep(2)
                await self.start_spider(spider_name)
            elif cmd_type == "get_status":
                response_channel = command.get("response_channel", REDIS_KEYS["CHANNEL_RESPONSES"])
                response = {
                    "type": "node_status_response", "node_id": self.node_id,
                    "status": "running" if self.running else "stopped",
                    "spiders": self.spider_status, "system": self.get_system_stats(),
                    "timestamp": datetime.now().isoformat()
                }
                await self.redis_client.publish(response_channel, json.dumps(response))
            elif cmd_type == "shutdown":
                logger.info("收到关闭命令")
                self.running = False
        except Exception as e:
            logger.error(f"处理命令 '{cmd_type}' 失败: {e}", exc_info=True)

    async def run(self):
        """运行节点"""
        if not await self.initialize():
            return

        self.running = True
        self.start_time = datetime.now()
        logger.info(f"爬虫节点开始运行: {self.node_id}，根目录: {self.base_dir}")

        await self.update_node_status("running")

        asyncio.create_task(self.renew_node_health_key())
        asyncio.create_task(self.listen_for_commands())

        while self.running:
            try:
                await self.check_spider_health()
                stats = {
                    "spider_count": len(self.processes),
                    "running_spiders": list(self.processes.keys()),
                    "uptime": (datetime.now() - self.start_time).total_seconds()
                }
                await self.update_node_status("running", stats)
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"主循环错误: {e}", exc_info=True)
                await asyncio.sleep(5)

        logger.info("爬虫节点停止运行，正在清理...")
        for spider_name in list(self.processes.keys()):
            await self.stop_spider(spider_name)

        await self.update_node_status("stopped")
        await self.cleanup_node()

        if self.redis_client:
            await self.redis_client.close()
        logger.info("节点清理完成。")

    async def cleanup_node(self):
        """清理节点注册"""
        try:
            if not self.redis_client:
                await self.initialize_redis()
                if not self.redis_client: return

            await self.redis_client.ping()
            await self.redis_client.srem(REDIS_KEYS["NODE_SET"], self.node_id)
            node_key = REDIS_KEYS["NODE_INFO"].format(node_id=self.node_id)
            await self.redis_client.delete(node_key)

            all_spider_keys = await self.redis_client.keys("spider_nodes:*")
            for key in all_spider_keys:
                await self.redis_client.srem(key, self.node_id)

            health_key = f"crawler_node_{self.node_id}"
            await self.redis_client.delete(health_key)
            logger.info(f"节点健康 Key 已清理: {health_key}")
            logger.info(f"节点清理完成: {self.node_id}")
        except redis.exceptions.ConnectionError:
            logger.error("Redis连接已断开，无法清理节点注册。")
            self.redis_client = None
        except Exception as e:
            logger.error(f"清理节点失败: {e}", exc_info=True)

def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description="爬虫节点管理器")
    # nargs='?' 表示这个参数是可选的，如果未提供，则使用 default 的值
    parser.add_argument("--node-id", nargs='?', default=os.getenv('NODE_ID'),
                        help="节点ID，默认从环境变量 NODE_ID 获取或自动生成")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="日志级别")
    args = parser.parse_args()

    # 如果命令行和环境变量都没有提供node-id，则会使用CrawlerNode类内部的自动生成逻辑
    node = CrawlerNode(node_id=args.node_id)
    # 确保日志级别在初始化时生效
    logging.getLogger().setLevel(args.log_level)

    try:
        asyncio.run(node.run())
    except KeyboardInterrupt:
        logger.info("收到键盘中断，停止节点")
    except Exception as e:
        logger.error(f"节点运行失败: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()