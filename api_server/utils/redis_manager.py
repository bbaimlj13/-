import redis.asyncio as redis
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
import uuid
import os
from shared.config import Config

logger = logging.getLogger(__name__)

class RedisManager:
    """
    一个单例的、异步的 Redis 连接管理器。
    """
    _instance: Optional['RedisManager'] = None
    _client: Optional[redis.Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self):
        """异步初始化 Redis 连接"""
        if self._client is None:
            try:
                self._client = redis.Redis(
                    host=os.getenv("REDIS_HOST", Config.REDIS_HOST),
                    port=int(os.getenv("REDIS_PORT", Config.REDIS_PORT)),
                    password=os.getenv("REDIS_PASSWORD", Config.REDIS_PASSWORD),
                    db=int(os.getenv("REDIS_DB", Config.REDIS_DB)),
                    decode_responses=True,
                    encoding='utf-8'
                )
                await self._client.ping()
                print("✅ Async Redis connection established successfully.")
            except Exception as e:
                print(f"❌ Failed to connect to Redis: {e}")
                raise

    async def close(self):
        """关闭 Redis 连接"""
        if self._client:
            await self._client.close()
            self._client = None
            print("🔌 Redis connection closed.")

    @property
    def client(self) -> redis.Redis:
        """获取 Redis 客户端实例"""
        if self._client is None:
            raise RuntimeError("RedisManager is not initialized. Call initialize() first.")
        return self._client

    # --- 任务管理相关方法 ---
    async def set_task_info(self, task_id: str, task_info: Dict[str, Any]):
        """保存任务信息 (Hash)"""
        try:
            key = f"task:{task_id}"
            
            # 创建一个可序列化的副本
            serializable_task_info = task_info.copy()
            
            # --- 新增/修改代码开始 ---
            # 遍历字典中的所有键值对
            for field, value in serializable_task_info.items():
                # 如果值是 None，则转换为空字符串
                if value is None:
                    serializable_task_info[field] = ""
                # 如果值是列表，则序列化为JSON字符串
                elif isinstance(value, list):
                    serializable_task_info[field] = json.dumps(value)
                # 如果值是字典，则序列化为JSON字符串
                elif isinstance(value, dict):
                    serializable_task_info[field] = json.dumps(value)
                # 如果值是datetime对象，则格式化为ISO 8601字符串
                elif isinstance(value, datetime):
                    serializable_task_info[field] = value.isoformat()
            # --- 新增/修改代码结束 ---

            # 使用序列化后的字典进行存储
            await self.client.hset(key, mapping=serializable_task_info)
            logger.debug(f"保存任务信息 (Hash): {key}")
        except Exception as e:
            logger.error(f"保存任务信息失败: {e}")
            raise
    
    async def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息 (Hash) 并进行反序列化"""
        try:
            key = f"task:{task_id}"
            task_info = await self.client.hgetall(key)
            
            if not task_info:
                return None
                
            # --- 完整的反序列化逻辑开始 ---
            # 遍历字典中的所有键值对
            for field, value in task_info.items():
                # 1. 处理应该是 None 的空字符串
                if value == "" and field in ['started_at', 'completed_at', 'paused_at', 'resumed_at', 'cancelled_at', 'error', 'node_id']:
                    task_info[field] = None
                    continue # 处理完 None 后，跳过后续的类型转换
                
                # 2. 尝试将值从JSON字符串反序列化（列表、字典）
                try:
                    parsed_value = json.loads(value)
                    task_info[field] = parsed_value
                    continue # 如果成功解析为JSON，跳过后续的类型转换
                except (json.JSONDecodeError, TypeError):
                    # 如果不是有效的JSON字符串，则继续尝试其他类型转换
                    pass

                # 3. 尝试将值转换为 datetime 对象
                try:
                    if 'at' in field: # 如 'created_at', 'started_at'
                        task_info[field] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        continue
                except (ValueError, TypeError):
                    pass
                
                # 4. 尝试将值转换为数字
                try:
                    # 优先尝试转换为整数
                    task_info[field] = int(value)
                except ValueError:
                    try:
                        # 如果失败，尝试转换为浮点数
                        task_info[field] = float(value)
                    except ValueError:
                        # 如果都失败，则保持为字符串
                        pass
            # --- 完整的反序列化逻辑结束 ---

            return task_info
        except Exception as e:
            logger.error(f"获取任务信息失败: {e}")
            return None
        
    async def list_tasks(self) -> List[Dict[str, Any]]:
        """列出所有任务"""
        try:
            tasks = []
            keys = await self.client.keys("task:*")
            
            for key in keys:
                data = await self.client.hgetall(key)
                if data:
                    tasks.append(data)
            
            return tasks
        except Exception as e:
            logger.error(f"列出任务失败: {e}")
            return []
    
    async def delete_task(self, task_id: str) -> bool:
        """删除任务及其相关数据"""
        try:
            key = f"task:{task_id}"
            await self.client.delete(key)
            await self.client.delete(f"task_stats:{task_id}")
            await self.client.delete(f"task_items:{task_id}")
            await self.client.delete(f"task_errors:{task_id}")
            logger.info(f"任务已删除: {task_id}")
            return True
        except Exception as e:
            logger.error(f"删除任务失败: {e}")
            return False
    
    # --- 队列管理相关方法 (Sorted Set) ---
    async def add_to_queue(self, queue_key: str, value: str, score: float = 5.0):
        """添加到队列（有序集合）"""
        try:
            await self.client.zadd(queue_key, {value: score})
            logger.debug(f"添加到队列: {queue_key}, 值: {value}, 分数: {score}")
        except Exception as e:
            logger.error(f"添加到队列失败: {e}")
            raise
    
    async def get_queue_size(self, queue_key: str) -> int:
        """获取队列大小"""
        try:
            return await self.client.zcard(queue_key)
        except Exception as e:
            logger.error(f"获取队列大小失败: {e}")
            return 0
    
    async def get_queue_items(self, queue_key: str, start: int = 0, end: int = -1) -> List[Dict[str, Any]]:
        """获取队列元素"""
        try:
            items = await self.client.zrange(queue_key, start, end, withscores=True)
            return [{"value": item[0], "score": item[1]} for item in items]
        except Exception as e:
            logger.error(f"获取队列元素失败: {e}")
            return []
    
    async def clear_queue(self, queue_key: str) -> int:
        """清空队列"""
        try:
            size = await self.get_queue_size(queue_key)
            await self.client.delete(queue_key)
            logger.warning(f"队列已清空: {queue_key}, 原有大小: {size}")
            return size
        except Exception as e:
            logger.error(f"清空队列失败: {e}")
            return 0

    # --- 统计信息相关方法 (Hash) ---
    async def get_stats(self, stats_key: str) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            data = await self.client.hgetall(stats_key)
            result = {}
            for key, value in data.items():
                try:
                    if '.' in value:
                        result[key] = float(value)
                    else:
                        result[key] = int(value)
                except ValueError:
                    result[key] = value
            return result
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
    
    async def update_stats(self, stats_key: str, updates: Dict[str, Any]):
        """更新统计信息"""
        try:
            if updates:
                await self.client.hset(stats_key, mapping=updates)
        except Exception as e:
            logger.error(f"更新统计信息失败: {e}")
    
    async def increment_stat(self, stats_key: str, field: str, amount: int = 1):
        """递增统计字段"""
        try:
            await self.client.hincrby(stats_key, field, amount)
        except Exception as e:
            logger.error(f"递增统计字段失败: {e}")

    # --- 列表管理相关方法 (List) ---
    async def add_to_list(self, list_key: str, value: Any, max_length: int = 1000):
        """添加到列表，并限制长度"""
        try:
        
            await self.client.lpush(list_key, json.dumps(value, default=str))
            if max_length > 0:
                await self.client.ltrim(list_key, 0, max_length - 1)
        except Exception as e:
            logger.error(f"添加到列表失败: {e}")
    
    async def get_list_items(self, list_key: str, start: int = 0, end: int = -1) -> List[Any]:
        """获取列表元素"""
        try:
       
            items = await self.client.lrange(list_key, start, end)
            result = []
            for item in items:
                try:
                    result.append(json.loads(item))
                except json.JSONDecodeError:
                    result.append(item)
            return result
        except Exception as e:
            logger.error(f"获取列表元素失败: {e}")
            return []

    # --- 集合管理相关方法 (Set) ---
    async def add_to_set(self, set_key: str, value: str):
        """添加到集合"""
        try:
           
            await self.client.sadd(set_key, value)
        except Exception as e:
            logger.error(f"添加到集合失败: {e}")
    
    async def get_set_items(self, set_key: str) -> List[str]:
        """获取集合元素"""
        try:

            return list(await self.client.smembers(set_key))
        except Exception as e:
            logger.error(f"获取集合元素失败: {e}")
            return []
    
    async def get_set_size(self, set_key: str) -> int:
        """获取集合大小"""
        try:
            # 【已修正】使用 self.client
            return await self.client.scard(set_key)
        except Exception as e:
            logger.error(f"获取集合大小失败: {e}")
            return 0
    
    async def remove_from_set(self, set_key: str, value: str) -> bool:
        """从集合中移除元素"""
        try:
            
            return await self.client.srem(set_key, value) > 0
        except Exception as e:
            logger.error(f"从集合中移除元素失败: {e}")
            return False

    # --- 发布/订阅相关方法 (Pub/Sub) ---
    async def publish_notification(self, message: Dict[str, Any]):
        """发布通知"""
        try:
            channel = "crawler:notifications"

            await self.client.publish(channel, json.dumps(message, default=str))
            logger.debug(f"发布通知: {channel}, 消息: {message}")
        except Exception as e:
            logger.error(f"发布通知失败: {e}")
    
    # 添加了正确的返回类型注解
    async def subscribe_to_channel(self, channel: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        订阅频道并返回一个异步生成器，用于迭代接收消息。
        这是一个“热点”方法，会持续运行直到被取消。
        """
        try:
          
            pubsub = self.client.pubsub()
            await pubsub.subscribe(channel)
            logger.info(f"已订阅频道: {channel}")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        yield data  # 使用 yield 将消息传递出去
                    except json.JSONDecodeError:
                        logger.warning(f"无法解析订阅消息: {message['data']}")
                        
        except asyncio.CancelledError:
            logger.info(f"订阅任务被取消: {channel}")
            await pubsub.close()
        except Exception as e:
            logger.error(f"订阅频道失败: {e}")
            await pubsub.close()
    
    # 监控相关方法
    async def get_crawler_node_count(self) -> int:
        """获取爬虫节点数量"""
        try:
            nodes = await self.client.smembers("crawler:nodes")
            return len(nodes)
        except Exception as e:
            logger.error(f"获取爬虫节点数量失败: {e}")
            return 0
    
    async def get_active_spider_count(self) -> int:
        """获取活跃爬虫数量"""
        try:
            count = 0
            spider_keys = await self.client.keys("spider:*:status")
            
            for key in spider_keys:
                status = await self.client.get(key)
                if status == "running":
                    count += 1
            
            return count
        except Exception as e:
            logger.error(f"获取活跃爬虫数量失败: {e}")
            return 0
    
    async def get_total_queue_size(self) -> int:
        """获取总队列大小"""
        try:
            total = 0
            queue_keys = await self.client.keys("*:start_urls")
            
            for key in queue_keys:
                size = await self.get_queue_size(key)
                total += size
            
            return total
        except Exception as e:
            logger.error(f"获取总队列大小失败: {e}")
            return 0
    
    async def get_total_items_processed(self) -> int:
        """获取总处理项目数"""
        try:
            count = 0
            stats_keys = await self.client.keys("*:stats")
            
            for key in stats_keys:
                stats = await self.get_stats(key)
                count += stats.get("items_processed", 0)
            
            return count
        except Exception as e:
            logger.error(f"获取总处理项目数失败: {e}")
            return 0
    
    async def get_total_items_failed(self) -> int:
        """获取总失败项目数"""
        try:
            count = 0
            stats_keys = await self.client.keys("*:stats")
            
            for key in stats_keys:
                stats = await self.get_stats(key)
                count += stats.get("items_failed", 0)
            
            return count
        except Exception as e:
            logger.error(f"获取总失败项目数失败: {e}")
            return 0
    
    async def get_processing_rate(self) -> float:
        """获取处理速率（项目/分钟）"""
        try:
            # 这里实现一个简化的速率计算
            # 实际应用中可能需要更复杂的逻辑
            return 0.0
        except Exception as e:
            logger.error(f"获取处理速率失败: {e}")
            return 0.0
    
    async def get_system_uptime(self) -> float:
        """获取系统运行时间（小时）"""
        try:
            # 获取系统启动时间
            start_time_key = "system:start_time"
            start_time_str = await self.client.get(start_time_key)
            
            if not start_time_str:
                # 如果没有记录启动时间，则设置当前时间为启动时间
                start_time_str = datetime.now().isoformat()
                await self.client.set(start_time_key, start_time_str)
                return 0.0
            
            start_time = datetime.fromisoformat(start_time_str)
            uptime = (datetime.now() - start_time).total_seconds() / 3600.0
            
            return uptime
        except Exception as e:
            logger.error(f"获取系统运行时间失败: {e}")
            return 0.0
    
    async def get_crawler_nodes(self) -> List[Dict[str, Any]]:
        """获取爬虫节点信息"""
        try:
            nodes = []
            node_keys = await self.client.keys("node:*:info")
            
            for key in node_keys:
                data = await self.client.get(key)
                if data:
                    try:
                        node_info = json.loads(data)
                        nodes.append(node_info)
                    except json.JSONDecodeError:
                        continue
            
            return nodes
        except Exception as e:
            logger.error(f"获取爬虫节点信息失败: {e}")
            return []
    
    async def get_tasks_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取任务摘要"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            tasks = []
            task_keys = await self.client.keys("task:*")
            
            for key in task_keys:
                data = await self.client.hgetall(key)
                if data:
                    
                    created_at_str = data.get("created_at")
                    if created_at_str:
                        try:
                            # 确保时间格式正确
                            if created_at_str.endswith('Z'):
                                created_at_str = created_at_str.replace('Z', '+00:00')
                            task_time = datetime.fromisoformat(created_at_str)
                            if task_time >= cutoff_time:
                                tasks.append(data)
                        except ValueError:
                            continue
            
            # 统计任务状态
            status_counts = {}
            for task in tasks:
                status = task.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                "total": len(tasks),
                "running": status_counts.get("running", 0),
                "completed": status_counts.get("completed", 0),
                "failed": status_counts.get("failed", 0),
                "pending": status_counts.get("pending", 0),
                "paused": status_counts.get("paused", 0),
                "cancelled": status_counts.get("cancelled", 0)
            }
        except Exception as e:
            logger.error(f"获取任务摘要失败: {e}")
            return {}
    
    async def get_redis_info(self) -> Dict[str, Any]:
        """获取Redis信息"""
        try:
            info = await self.client.info()
            
            # 提取关键信息
            result = {
                "version": info.get("redis_version", "unknown"),
                "uptime": info.get("uptime_in_seconds", 0),
                "memory": {
                    "used": info.get("used_memory_human", "0B"),
                    "peak": info.get("used_memory_peak_human", "0B"),
                    "fragmentation": info.get("mem_fragmentation_ratio", 0)
                },
                "clients": {
                    "connected": info.get("connected_clients", 0),
                    "max_connections": info.get("maxclients", 0)
                },
                "stats": {
                    "total_connections": info.get("total_connections_received", 0),
                    "total_commands": info.get("total_commands_processed", 0),
                    "instantaneous_ops": info.get("instantaneous_ops_per_sec", 0)
                },
                "keyspace": {
                    "keys": sum(int(db.get("keys", 0)) for db in info.get("db", {}).values()),
                    "expires": sum(int(db.get("expires", 0)) for db in info.get("db", {}).values())
                }
            }
            
            return result
        except Exception as e:
            logger.error(f"获取Redis信息失败: {e}")
            return {}
    
    async def get_system_alerts(self, severity: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """获取系统警报"""
        try:
            alert_key = "system:alerts"
            alerts = await self.get_list_items(alert_key, 0, limit - 1)
            
            if severity:
                alerts = [alert for alert in alerts if alert.get("severity") == severity]
            
            return alerts
        except Exception as e:
            logger.error(f"获取系统警报失败: {e}")
            return []
    
    async def save_alert(self, alert: Dict[str, Any]):
        """保存警报"""
        try:
            alert_key = "system:alerts"
            await self.add_to_list(alert_key, alert, 1000)  # 最多保存1000个警报
        except Exception as e:
            logger.error(f"保存警报失败: {e}")
    
    async def get_system_logs(self, level: Optional[str] = None, source: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取系统日志"""
        try:
            log_key = "system:logs"
            logs = await self.get_list_items(log_key, 0, limit - 1)
            
            # 应用过滤器
            filtered_logs = []
            for log in logs:
                if level and log.get("level") != level:
                    continue
                if source and log.get("source") != source:
                    continue
                filtered_logs.append(log)
            
            return filtered_logs
        except Exception as e:
            logger.error(f"获取系统日志失败: {e}")
            return []
    
    async def save_log(self, log: Dict[str, Any]):
        """保存日志"""
        try:
            log_key = "system:logs"
            await self.add_to_list(log_key, log, 10000)  # 最多保存10000条日志
        except Exception as e:
            logger.error(f"保存日志失败: {e}")
    
    async def get_metric_history(self, metric: str, period: str) -> List[Dict[str, Any]]:
        """获取指标历史数据"""
        try:
            # 根据周期确定时间范围和精度
            periods = {
                "1h": (60, 1),   # 1分钟间隔，60个点
                "6h": (72, 5),   # 5分钟间隔，72个点
                "24h": (96, 15), # 15分钟间隔，96个点
                "7d": (168, 60), # 1小时间隔，168个点
                "30d": (120, 360) # 6小时间隔，120个点
            }
            
            if period not in periods:
                period = "1h"
            
            count, interval_minutes = periods[period]
            history_key = f"metrics:{metric}:{period}"
            
            # 获取历史数据
            data = await self.get_list_items(history_key, 0, count - 1)
            
            # 如果数据不足，生成模拟数据（实际应用中应从时间序列数据库获取）
            if len(data) < count:
                data = self._generate_mock_metric_data(metric, count, interval_minutes)
            
            return data
        except Exception as e:
            logger.error(f"获取指标历史数据失败: {e}")
            return []
    
    async def get_recent_items(self, items_key: str, count: int = 10) -> List[Dict[str, Any]]:
        """获取最近的项目"""
        try:
            return await self.get_list_items(items_key, 0, count - 1)
        except Exception as e:
            logger.error(f"获取最近项目失败: {e}")
            return []
    
    async def clear_old_alerts(self, days: int) -> int:
        """清理旧警报"""
        try:
            # 这里实现一个简化的清理逻辑
            # 实际应用中可能需要更复杂的基于时间的清理
            alert_key = "system:alerts"
            alerts = await self.get_list_items(alert_key)
            
            # 计算截止时间
            cutoff_time = datetime.now() - timedelta(days=days)
            
            # 过滤出需要保留的警报
            kept_alerts = []
            for alert in alerts:
                alert_time_str = alert.get("timestamp")
                if alert_time_str:
                    try:
                        alert_time = datetime.fromisoformat(alert_time_str.replace('Z', '+00:00'))
                        if alert_time >= cutoff_time:
                            kept_alerts.append(alert)
                    except (ValueError, KeyError):
                        kept_alerts.append(alert)
                else:
                    kept_alerts.append(alert)
            
            # 清空并重新保存
            await self.client.delete(alert_key)
            for alert in kept_alerts:
                await self.add_to_list(alert_key, alert)
            
            cleared_count = len(alerts) - len(kept_alerts)
            return cleared_count
            
        except Exception as e:
            logger.error(f"清理旧警报失败: {e}")
            return 0
    
    def _generate_mock_metric_data(self, metric: str, count: int, interval_minutes: int) -> List[Dict[str, Any]]:
        """生成模拟指标数据（用于演示）"""
        import random
        from datetime import datetime, timedelta
        
        data = []
        now = datetime.now()
        
        # 不同指标的基础值
        base_values = {
            "cpu_usage": 20,
            "memory_usage": 40,
            "queue_size": 50,
            "items_processed": 100,
            "active_nodes": 3
        }
        
        base_value = base_values.get(metric, 50)
        
        for i in range(count):
            timestamp = (now - timedelta(minutes=i * interval_minutes)).isoformat()
            
            # 生成一些波动
            if metric == "cpu_usage":
                value = base_value + random.uniform(-15, 30)
                value = max(0, min(100, value))
            elif metric == "memory_usage":
                value = base_value + random.uniform(-10, 20)
                value = max(0, min(100, value))
            elif metric == "queue_size":
                value = base_value + random.uniform(-30, 40)
                value = max(0, value)
            elif metric == "items_processed":
                value = base_value + i * 10 + random.uniform(-5, 15)
                value = max(0, value)
            elif metric == "active_nodes":
                value = base_value + random.choice([-1, 0, 0, 1])
                value = max(0, min(10, value))
            else:
                value = base_value + random.uniform(-20, 20)
                value = max(0, value)
            
            data.append({
                "timestamp": timestamp,
                "value": round(value, 2)
            })
        
        # 按时间顺序排序
        data.sort(key=lambda x: x["timestamp"])
        
        return data
redis_manager_instance = RedisManager()

# 定义依赖项注入函数
async def get_redis_manager() -> RedisManager:
    """
    依赖项注入函数，用于在路由中获取 RedisManager 实例。
    """
    if redis_manager_instance._client is None:
        await redis_manager_instance.initialize()
    return redis_manager_instance