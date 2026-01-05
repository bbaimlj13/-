#!/usr/bin/env python3
"""
API客户端示例
用于演示如何与分布式爬虫系统的API进行交互
"""

import requests
import json
import time
import argparse
from typing import Dict, List, Any, Optional
from datetime import datetime

class CrawlerAPIClient:
    """分布式爬虫系统API客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        """
        初始化API客户端
        
        Args:
            base_url: API服务器地址
            api_key: API密钥（可选）
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'CrawlerAPIClient/1.0.0',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})
        
        # 测试连接
        self.test_connection()
    
    def test_connection(self):
        """测试API连接"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            response.raise_for_status()
            print(f"✅ API连接成功: {self.base_url}")
            return True
        except Exception as e:
            print(f"❌ API连接失败: {e}")
            return False
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            response = self.session.get(f"{self.base_url}/system/info")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取系统信息失败: {e}")
            return {}
    
    def get_available_spiders(self) -> List[Dict[str, Any]]:
        """获取可用爬虫列表"""
        try:
            response = self.session.get(f"{self.base_url}/api/crawler/spiders")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取爬虫列表失败: {e}")
            return []
    
    def create_crawler_task(self, spider_name: str, urls: List[str], 
                           priority: int = 5, max_items: int = 100) -> Dict[str, Any]:
        """
        创建爬虫任务
        
        Args:
            spider_name: 爬虫名称
            urls: 起始URL列表
            priority: 优先级(1-10)
            max_items: 最大抓取数量
        
        Returns:
            任务创建结果
        """
        try:
            payload = {
                "spider_name": spider_name,
                "urls": urls,
                "priority": priority,
                "max_items": max_items
            }
            
            response = self.session.post(
                f"{self.base_url}/api/crawler/tasks",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            print(f"✅ 任务创建成功: {result.get('task_id')}")
            return result
            
        except Exception as e:
            print(f"❌ 创建任务失败: {e}")
            return {}
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        try:
            response = self.session.get(f"{self.base_url}/api/crawler/tasks/{task_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取任务状态失败: {e}")
            return {}
    
    def list_tasks(self, status: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """列出任务"""
        try:
            params = {"limit": limit}
            if status:
                params["status"] = status
            
            response = self.session.get(
                f"{self.base_url}/api/crawler/tasks",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"列出任务失败: {e}")
            return []
    
    def start_spider(self, spider_name: str, urls: List[str] = None) -> Dict[str, Any]:
        """启动爬虫"""
        try:
            payload = {"urls": urls or []}
            
            response = self.session.post(
                f"{self.base_url}/api/crawler/spiders/{spider_name}/start",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            print(f"✅ 爬虫启动成功: {spider_name}")
            return result
            
        except Exception as e:
            print(f"❌ 启动爬虫失败: {e}")
            return {}
    
    def stop_spider(self, spider_name: str) -> Dict[str, Any]:
        """停止爬虫"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/crawler/spiders/{spider_name}/stop"
            )
            response.raise_for_status()
            
            result = response.json()
            print(f"✅ 爬虫停止成功: {spider_name}")
            return result
            
        except Exception as e:
            print(f"❌ 停止爬虫失败: {e}")
            return {}
    
    def get_spider_status(self, spider_name: str) -> Dict[str, Any]:
        """获取爬虫状态"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/crawler/spiders/{spider_name}/status"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取爬虫状态失败: {e}")
            return {}
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计"""
        try:
            response = self.session.get(f"{self.base_url}/api/monitor/stats")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取系统统计失败: {e}")
            return {}
    
    def get_crawler_nodes(self) -> List[Dict[str, Any]]:
        """获取爬虫节点"""
        try:
            response = self.session.get(f"{self.base_url}/api/monitor/nodes")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取爬虫节点失败: {e}")
            return []
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        try:
            response = self.session.get(f"{self.base_url}/api/monitor/performance")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取性能指标失败: {e}")
            return {}
    
    def get_recent_logs(self, level: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取最近日志"""
        try:
            params = {"limit": limit}
            if level:
                params["level"] = level
            
            response = self.session.get(
                f"{self.base_url}/api/monitor/logs",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取日志失败: {e}")
            return []
    
    def batch_create_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量创建任务"""
        try:
            payload = {"tasks": tasks}
            
            response = self.session.post(
                f"{self.base_url}/api/crawler/tasks/batch",
                json=payload
            )
            response.raise_for_status()
            
            results = response.json()
            print(f"✅ 批量创建完成: 成功 {len(results)} 个任务")
            return results
            
        except Exception as e:
            print(f"❌ 批量创建失败: {e}")
            return []
    
    def wait_for_task_completion(self, task_id: str, timeout: int = 300, 
                                interval: int = 5) -> bool:
        """
        等待任务完成
        
        Args:
            task_id: 任务ID
            timeout: 超时时间（秒）
            interval: 检查间隔（秒）
        
        Returns:
            是否成功完成
        """
        start_time = time.time()
        
        print(f"⏳ 等待任务完成: {task_id}")
        
        while time.time() - start_time < timeout:
            try:
                task_status = self.get_task_status(task_id)
                status = task_status.get("status", "unknown")
                
                if status in ["completed", "failed", "cancelled"]:
                    if status == "completed":
                        print(f"✅ 任务完成: {task_id}")
                    else:
                        print(f"⚠️ 任务结束状态: {status}, 任务ID: {task_id}")
                    return status == "completed"
                
                # 显示进度
                stats = task_status.get("stats", {})
                processed = stats.get("processed_items", 0)
                total = stats.get("total_items", 0)
                
                if total > 0:
                    progress = (processed / total) * 100
                    print(f"📊 任务进度: {progress:.1f}% ({processed}/{total})")
                
                time.sleep(interval)
                
            except Exception as e:
                print(f"⚠️ 检查任务状态失败: {e}")
                time.sleep(interval)
        
        print(f"⏰ 等待任务超时: {task_id}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="分布式爬虫系统API客户端")
    parser.add_argument("--url", default="http://localhost:8000", help="API服务器地址")
    parser.add_argument("--api-key", help="API密钥")
    parser.add_argument("--command", choices=[
        "info", "spiders", "create-task", "list-tasks", "start-spider", 
        "stop-spider", "status", "stats", "nodes", "performance", "logs"
    ], default="info", help="执行命令")
    parser.add_argument("--spider", help="爬虫名称")
    parser.add_argument("--urls", help="URL列表，用逗号分隔")
    parser.add_argument("--task-id", help="任务ID")
    parser.add_argument("--priority", type=int, default=5, help="任务优先级(1-10)")
    parser.add_argument("--max-items", type=int, default=100, help="最大抓取数量")
    
    args = parser.parse_args()
    
    # 创建客户端
    client = CrawlerAPIClient(base_url=args.url, api_key=args.api_key)
    
    # 执行命令
    if args.command == "info":
        # 获取系统信息
        info = client.get_system_info()
        print(json.dumps(info, indent=2, ensure_ascii=False))
    
    elif args.command == "spiders":
        # 获取爬虫列表
        spiders = client.get_available_spiders()
        print(f"可用爬虫 ({len(spiders)} 个):")
        for spider in spiders:
            print(f"  - {spider['name']}: {spider['description']}")
    
    elif args.command == "create-task":
        # 创建任务
        if not args.spider:
            print("❌ 请指定爬虫名称 (--spider)")
            return
        
        urls = args.urls.split(',') if args.urls else []
        if not urls:
            print("❌ 请指定URL列表 (--urls)")
            return
        
        result = client.create_crawler_task(
            spider_name=args.spider,
            urls=urls,
            priority=args.priority,
            max_items=args.max_items
        )
        
        if result and args.task_id:
            # 等待任务完成
            client.wait_for_task_completion(result.get("task_id"))
    
    elif args.command == "list-tasks":
        # 列出任务
        tasks = client.list_tasks()
        print(f"任务列表 ({len(tasks)} 个):")
        for task in tasks[:10]:  # 只显示前10个
            task_id = task.get("task_id", "unknown")
            spider_name = task.get("spider_name", "unknown")
            status = task.get("status", "unknown")
            created = task.get("created_at", "")
            
            print(f"  - {task_id}: {spider_name} [{status}] ({created})")
    
    elif args.command == "start-spider":
        # 启动爬虫
        if not args.spider:
            print("❌ 请指定爬虫名称 (--spider)")
            return
        
        urls = args.urls.split(',') if args.urls else []
        result = client.start_spider(args.spider, urls)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "stop-spider":
        # 停止爬虫
        if not args.spider:
            print("❌ 请指定爬虫名称 (--spider)")
            return
        
        result = client.stop_spider(args.spider)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "status":
        # 获取任务状态
        if not args.task_id:
            print("❌ 请指定任务ID (--task-id)")
            return
        
        status = client.get_task_status(args.task_id)
        print(json.dumps(status, indent=2, ensure_ascii=False))
    
    elif args.command == "stats":
        # 获取系统统计
        stats = client.get_system_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    elif args.command == "nodes":
        # 获取爬虫节点
        nodes = client.get_crawler_nodes()
        print(f"爬虫节点 ({len(nodes)} 个):")
        for node in nodes:
            node_id = node.get("id", "unknown")
            status = node.get("status", "unknown")
            hostname = node.get("hostname", "unknown")
            
            print(f"  - {node_id}: {hostname} [{status}]")
    
    elif args.command == "performance":
        # 获取性能指标
        metrics = client.get_performance_metrics()
        print(json.dumps(metrics, indent=2, ensure_ascii=False))
    
    elif args.command == "logs":
        # 获取日志
        logs = client.get_recent_logs(limit=10)
        print(f"最近日志 ({len(logs)} 条):")
        for log in logs:
            timestamp = log.get("timestamp", "")
            level = log.get("level", "INFO")
            message = log.get("message", "")
            source = log.get("source", "")
            
            print(f"  [{timestamp}] [{level}] [{source}] {message}")

if __name__ == "__main__":
    main()