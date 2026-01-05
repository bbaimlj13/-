from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Body, Depends
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import redis.asyncio as redis
import json
import logging
import asyncio
from datetime import datetime
import uuid

from api_server.utils.redis_manager import RedisManager, get_redis_manager
from shared.config import Config
from shared.models import CreateTaskRequest, TaskResponse, CrawlerTask 
from shared.constants import TARGET_URLS

logger = logging.getLogger(__name__)
router = APIRouter()

class TaskStats(BaseModel):
    """任务统计"""
    task_id: str = Field(..., description="任务ID")
    spider_name: str = Field(..., description="爬虫名称")
    total_items: int = Field(default=0, description="总项目数")
    processed_items: int = Field(default=0, description="已处理项目数")
    failed_items: int = Field(default=0, description="失败项目数")
    queue_size: int = Field(default=0, description="队列大小")
    dupefilter_size: int = Field(default=0, description="去重集合大小")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration_seconds: Optional[float] = Field(None, description="持续时间(秒)")

class SpiderInfo(BaseModel):
    """爬虫信息"""
    name: str = Field(..., description="爬虫名称")
    description: str = Field(..., description="爬虫描述")
    domains: List[str] = Field(..., description="允许的域名")
    start_urls: List[str] = Field(..., description="起始URL")
    max_concurrent: int = Field(..., description="最大并发数")
    rate_limit: float = Field(..., description="速率限制")

class BatchTaskRequest(BaseModel):
    """批量任务请求"""
    tasks: List[CreateTaskRequest] = Field(..., description="任务列表")
    parallel: bool = Field(default=True, description="是否并行执行")

@router.get("/spiders", response_model=List[SpiderInfo])
async def get_available_spiders():
    """获取可用的爬虫列表"""
    try:
        spiders = [
            {
                "name": "bjx_spider",
                "description": "北极星电力网爬虫，抓取电力行业新闻",
                "domains": ["bjx.com.cn", "guangfu.bjx.com.cn", "fd.bjx.com.cn"],
                "start_urls": ["https://www.bjx.com.cn/"],
                "max_concurrent": 4,
                "rate_limit": 1.0
            },
            {
                "name": "nmc_spider",
                "description": "中央气象台爬虫，抓取气象预报和预警信息",
                "domains": ["nmc.cn"],
                "start_urls": [target["url"] for target in TARGET_URLS],
                "max_concurrent": 3,
                "rate_limit": 2.0
            },
            {
                "name": "fgw_spider",
                "description": "国家发改委爬虫，抓取能源政策文件",
                "domains": ["ndrc.gov.cn"],
                "start_urls": ["https://www.ndrc.gov.cn/xxgk/jd/jd/"],
                "max_concurrent": 2,
                "rate_limit": 3.0
            },
            {
                "name": "nyj_spider",
                "description": "国家能源局爬虫，抓取能源行业新闻",
                "domains": ["nea.gov.cn"],
                "start_urls": ["https://www.nea.gov.cn/"],
                "max_concurrent": 3,
                "rate_limit": 2.0
            },
            {
            "name": "kzs_spider",
            "description": "可再生能源学会爬虫，抓取可再生能源动态",
            "domains": ["cres.org.cn"],
            "start_urls": ["http://www.cres.org.cn/"],
            "max_concurrent": 2,
            "rate_limit": 3.0
            },
            {
                "name": "cec_spider",
                "description": "中电联网站爬虫，抓取电力行业报告和数据",
                "domains": ["cec.org.cn"],
                "start_urls": ["https://www.cec.org.cn/"],
                "max_concurrent": 3,
                "rate_limit": 2.0
            }
        ]
        
        return spiders
        
    except Exception as e:
        logger.error(f"获取爬虫列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取爬虫列表失败: {str(e)}")

@router.post("/tasks", response_model=TaskResponse)
async def create_crawler_task(
    task_request: CreateTaskRequest,
    background_tasks: BackgroundTasks,
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """创建爬虫任务"""
    try:
        # 生成任务ID
        task_id = f"task_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 创建任务数据
        task_data = CrawlerTask(
            task_id=task_id,
            spider_name=task_request.spider_name,
            urls=task_request.urls,
            config=task_request.config,
            priority=task_request.priority,
            max_items=task_request.max_items,
            status="pending",
            created_at=datetime.now()
        )
        
        # 保存任务信息到Redis
        await redis_manager.set_task_info(task_id, task_data.dict())
        
        # 将URL添加到Redis队列
        queue_key = f"{task_request.spider_name}:start_urls"
        added_count = 0
        
        for url in task_request.urls:
            # 使用有序集合支持优先级
            score = task_request.priority * 10 + (10 - added_count % 10) / 10.0
            await redis_manager.add_to_queue(queue_key, url, score)
            added_count += 1
        
        # 发送任务创建通知
        await redis_manager.publish_notification({
            "type": "task_created",
            "task_id": task_id,
            "spider_name": task_request.spider_name,
            "urls_count": len(task_request.urls),
            "timestamp": datetime.now().isoformat()
        })
        
        # 在后台启动任务处理
        background_tasks.add_task(
            process_crawler_task,
            task_id,
            task_request.spider_name,
            redis_manager
        )
        
        logger.info(f"爬虫任务创建成功: {task_id}, 爬虫: {task_request.spider_name}, URL数量: {len(task_request.urls)}")
        
        return TaskResponse(
            task_id=task_id,
            spider_name=task_request.spider_name,
            urls_count=len(task_request.urls),
            status="created",
            created_at=datetime.now(),
            queue_key=queue_key
        )
        
    except Exception as e:
        logger.error(f"创建爬虫任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建爬虫任务失败: {str(e)}")

@router.post("/tasks/batch", response_model=List[TaskResponse])
async def create_batch_tasks(
    batch_request: BatchTaskRequest,
    background_tasks: BackgroundTasks,
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """批量创建爬虫任务"""
    try:
        responses = []
        
        for task_request in batch_request.tasks:
            try:
                # 创建单个任务
                task_id = f"task_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                task_data = CrawlerTask(
                    task_id=task_id,
                    spider_name=task_request.spider_name,
                    urls=task_request.urls,
                    config=task_request.config,
                    priority=task_request.priority,
                    max_items=task_request.max_items,
                    status="pending",
                    created_at=datetime.now()
                )
                
                # 保存任务信息
                await redis_manager.set_task_info(task_id, task_data.dict())
                
                # 添加URL到队列
                queue_key = f"{task_request.spider_name}:start_urls"
                added_count = 0
                
                for url in task_request.urls:
                    score = task_request.priority * 10 + (10 - added_count % 10) / 10.0
                    await redis_manager.add_to_queue(queue_key, url, score)
                    added_count += 1
                
                # 创建响应
                response = TaskResponse(
                    task_id=task_id,
                    spider_name=task_request.spider_name,
                    urls_count=len(task_request.urls),
                    status="created",
                    created_at=datetime.now(),
                    queue_key=queue_key
                )
                
                responses.append(response)
                
                # 启动任务处理
                background_tasks.add_task(
                    process_crawler_task,
                    task_id,
                    task_request.spider_name,
                    redis_manager
                )
                
            except Exception as e:
                logger.error(f"批量创建任务失败(单个任务): {e}")
                # 继续处理其他任务
        
        logger.info(f"批量创建任务完成: 成功 {len(responses)}/{len(batch_request.tasks)} 个任务")
        
        return responses
        
    except Exception as e:
        logger.error(f"批量创建任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量创建任务失败: {str(e)}")

@router.get("/tasks", response_model=List[CrawlerTask])
async def list_tasks(
    status: Optional[str] = None,
    spider_name: Optional[str] = None,
    limit: int = 50,
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """列出所有爬虫任务"""
    try:
        tasks = []
        # 获取所有任务的 key
        task_ids = await redis_manager.client.keys("task:*")
        
        for task_id_key in task_ids:
            # 从 key 中提取 task_id (例如从 "task:123" 得到 "123")
            task_id = task_id_key.split(":", 1)[1]
            
            # 2. 使用 get_task_info 来获取经过反序列化的任务数据
            task_data = await redis_manager.get_task_info(task_id)
            
            if task_data:
                tasks.append(task_data)
        
        # ... 过滤和分页逻辑 (保持不变) ...
        if status:
            tasks = [task for task in tasks if task.get("status") == status]
        if spider_name:
            tasks = [task for task in tasks if task.get("spider_name") == spider_name]
        
        return tasks[:limit]

    except Exception as e:
        logger.error(f"列出任务失败: {e}")
        return []

@router.get("/tasks/{task_id}", response_model=Dict[str, Any])
async def get_task_details(
    task_id: str,
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """获取任务详细信息"""
    try:
        task_info = await redis_manager.get_task_info(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
        
        # 获取统计信息
        stats_key = f"task_stats:{task_id}"
        stats = await redis_manager.get_stats(stats_key)
        
        # 获取最近的项目
        items_key = f"task_items:{task_id}"
        recent_items = await redis_manager.get_recent_items(items_key, 10)
        
        # 获取错误信息
        errors_key = f"task_errors:{task_id}"
        recent_errors = await redis_manager.get_list_items(errors_key, 0, 9)
        
        result = {
            **task_info,
            "stats": stats,
            "recent_items": recent_items,
            "recent_errors": recent_errors
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务详情失败: {str(e)}")

@router.get("/tasks/{task_id}/stats", response_model=TaskStats)
async def get_task_stats(
    task_id: str,
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """获取任务统计信息"""
    try:
        task_info = await redis_manager.get_task_info(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
        
        # 获取详细统计
        stats_key = f"task_stats:{task_id}"
        stats = await redis_manager.get_stats(stats_key)
        
        # 计算持续时间
        duration_seconds = None
        start_time = task_info.get("started_at")
        end_time = task_info.get("completed_at")
        
        if start_time:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if end_time:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                duration_seconds = (end_dt - start_dt).total_seconds()
            else:
                duration_seconds = (datetime.now() - start_dt).total_seconds()
        
        # 获取队列大小
        spider_name = task_info.get("spider_name")
        queue_key = f"{spider_name}:start_urls"
        queue_size = await redis_manager.get_queue_size(queue_key)
        
        # 获取去重集合大小
        dupefilter_key = f"{spider_name}:dupefilter"
        dupefilter_size = await redis_manager.get_set_size(dupefilter_key)
        
        return TaskStats(
            task_id=task_id,
            spider_name=spider_name,
            total_items=stats.get("total_items", 0),
            processed_items=stats.get("processed_items", 0),
            failed_items=stats.get("failed_items", 0),
            queue_size=queue_size,
            dupefilter_size=dupefilter_size,
            start_time=datetime.fromisoformat(start_time.replace('Z', '+00:00')) if start_time else None,
            end_time=datetime.fromisoformat(end_time.replace('Z', '+00:00')) if end_time else None,
            duration_seconds=duration_seconds
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务统计失败: {str(e)}")

@router.post("/tasks/{task_id}/pause")
async def pause_task(
    task_id: str,
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """暂停任务"""
    try:
        task_info = await redis_manager.get_task_info(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
        
        if task_info.get("status") not in ["running", "pending"]:
            raise HTTPException(status_code=400, detail=f"任务状态 {task_info.get('status')} 无法暂停")
        
        # 更新任务状态
        task_info["status"] = "paused"
        task_info["paused_at"] = datetime.now().isoformat()
        await redis_manager.set_task_info(task_id, task_info)
        
        # 发送暂停通知
        await redis_manager.publish_notification({
            "type": "task_paused",
            "task_id": task_id,
            "spider_name": task_info.get("spider_name"),
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"任务已暂停: {task_id}")
        
        return {"success": True, "message": f"任务 {task_id} 已暂停"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"暂停任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"暂停任务失败: {str(e)}")

@router.post("/tasks/{task_id}/resume")
async def resume_task(
    task_id: str,
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """恢复任务"""
    try:
        task_info = await redis_manager.get_task_info(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
        
        if task_info.get("status") != "paused":
            raise HTTPException(status_code=400, detail=f"任务状态 {task_info.get('status')} 无法恢复")
        
        # 更新任务状态
        task_info["status"] = "running"
        task_info["resumed_at"] = datetime.now().isoformat()
        await redis_manager.set_task_info(task_id, task_info)
        
        # 发送恢复通知
        await redis_manager.publish_notification({
            "type": "task_resumed",
            "task_id": task_id,
            "spider_name": task_info.get("spider_name"),
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"任务已恢复: {task_id}")
        
        return {"success": True, "message": f"任务 {task_id} 已恢复"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"恢复任务失败: {str(e)}")

@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """取消任务"""
    try:
        task_info = await redis_manager.get_task_info(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
        
        if task_info.get("status") in ["completed", "failed", "cancelled"]:
            raise HTTPException(status_code=400, detail=f"任务状态 {task_info.get('status')} 无法取消")
        
        # 更新任务状态
        task_info["status"] = "cancelled"
        task_info["cancelled_at"] = datetime.now().isoformat()
        await redis_manager.set_task_info(task_id, task_info)
        
        # 发送取消通知
        await redis_manager.publish_notification({
            "type": "task_cancelled",
            "task_id": task_id,
            "spider_name": task_info.get("spider_name"),
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"任务已取消: {task_id}")
        
        return {"success": True, "message": f"任务 {task_id} 已取消"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")

@router.post("/spiders/{spider_name}/start")
async def start_spider(
    spider_name: str,
    urls: List[str] = Body(default=[], embed=True),
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """启动爬虫"""
    try:
        # 验证爬虫名称
        valid_spiders = ["bjx_spider", "nmc_spider", "fgw_spider", "nyj_spider", "kzs_spider", "cec_spider"]
        if spider_name not in valid_spiders:
            raise HTTPException(status_code=400, detail=f"无效的爬虫名称，可选值: {', '.join(valid_spiders)}")
        
        # 如果有提供URL，添加到队列
        if urls:
            queue_key = f"{spider_name}:start_urls"
            for url in urls:
                await redis_manager.add_to_queue(queue_key, url, 5)  # 默认优先级5
        
        # 发送爬虫启动通知
        await redis_manager.publish_notification({
            "type": "spider_started",
            "spider_name": spider_name,
            "urls_count": len(urls),
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"爬虫已启动: {spider_name}, URL数量: {len(urls)}")
        
        return {
            "success": True,
            "message": f"爬虫 {spider_name} 已启动",
            "queue_key": f"{spider_name}:start_urls",
            "urls_added": len(urls)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动爬虫失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动爬虫失败: {str(e)}")

@router.post("/spiders/{spider_name}/stop")
async def stop_spider(
    spider_name: str,
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """停止爬虫"""
    try:
        # 发送爬虫停止通知
        await redis_manager.publish_notification({
            "type": "spider_stopped",
            "spider_name": spider_name,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"爬虫已停止: {spider_name}")
        
        return {"success": True, "message": f"爬虫 {spider_name} 已停止"}
        
    except Exception as e:
        logger.error(f"停止爬虫失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止爬虫失败: {str(e)}")

@router.get("/spiders/{spider_name}/status")
async def get_spider_status(
    spider_name: str,
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """获取爬虫状态"""
    try:
        # 获取队列大小
        queue_key = f"{spider_name}:start_urls"
        queue_size = await redis_manager.get_queue_size(queue_key)
        
        # 获取去重集合大小
        dupefilter_key = f"{spider_name}:dupefilter"
        dupefilter_size = await redis_manager.get_set_size(dupefilter_key)
        
        # 获取活跃爬虫节点数
        spider_nodes_key = f"spider_nodes:{spider_name}"
        spider_nodes = await redis_manager.get_set_items(spider_nodes_key)
        
        # 获取爬虫统计
        stats_key = f"spider_stats:{spider_name}"
        stats = await redis_manager.get_stats(stats_key)
        
        return {
            "spider_name": spider_name,
            "queue_size": queue_size,
            "dupefilter_size": dupefilter_size,
            "active_nodes": len(spider_nodes),
            "active_node_ids": list(spider_nodes),
            "stats": stats,
            "last_activity": stats.get("last_activity", None)
        }
        
    except Exception as e:
        logger.error(f"获取爬虫状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取爬虫状态失败: {str(e)}")

@router.get("/queue/{queue_key}")
async def get_queue_info(
    queue_key: str,
    start: int = Query(0, description="起始位置", ge=0),
    end: int = Query(49, description="结束位置", ge=0),
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """获取队列信息"""
    try:
        # 获取队列大小
        queue_size = await redis_manager.get_queue_size(queue_key)
        
        # 获取队列元素
        queue_items = await redis_manager.get_queue_items(queue_key, start, end)
        
        return {
            "queue_key": queue_key,
            "size": queue_size,
            "items": queue_items,
            "range": {"start": start, "end": min(end, queue_size - 1)}
        }
        
    except Exception as e:
        logger.error(f"获取队列信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取队列信息失败: {str(e)}")

@router.delete("/queue/{queue_key}/clear")
async def clear_queue(
    queue_key: str,
    redis_manager: RedisManager = Depends(get_redis_manager)
):
    """清空队列"""
    try:
        # 获取当前队列大小
        queue_size = await redis_manager.get_queue_size(queue_key)
        
        # 清空队列
        await redis_manager.clear_queue(queue_key)
        
        logger.warning(f"队列已清空: {queue_key}, 原有大小: {queue_size}")
        
        return {
            "success": True,
            "message": f"队列 {queue_key} 已清空",
            "cleared_items": queue_size
        }
        
    except Exception as e:
        logger.error(f"清空队列失败: {e}")
        raise HTTPException(status_code=500, detail=f"清空队列失败: {str(e)}")
async def process_crawler_task(task_id: str, spider_name: str, redis_manager: RedisManager):
    """处理爬虫任务的背景任务"""
    # 使用 try...except 包裹整个函数，确保任何错误都能被记录
    try:
        logger.info(f"开始处理爬虫任务: {task_id}, 爬虫: {spider_name}")
        
        # 1. 获取并更新任务状态为 running
        task_info = await redis_manager.get_task_info(task_id)
        if not task_info:
            logger.warning(f"任务信息不存在，可能已被删除: {task_id}")
            return

        task_info["status"] = "running"
        task_info["started_at"] = datetime.now().isoformat()
        await redis_manager.set_task_info(task_id, task_info)
        
        # 2. 发送任务开始的通知 (这是你原有的业务逻辑)
        await redis_manager.publish_notification({
            "type": "task_started",
            "task_id": task_id,
            "spider_name": spider_name,
            "timestamp": datetime.now().isoformat()
        })
        
        # 3. [核心] 向爬虫节点管理器发布启动命令
        command_channel = "channel:commands"  # 确保这个频道名称与爬虫节点管理器监听的一致
        start_command = {
            "type": "start_spider",
            "spider_name": spider_name,
            "task_id": task_id, # 附带task_id，方便日志追踪
            "timestamp": datetime.now().isoformat()
        }
        
        # 使用 redis_manager.client 直接发布原始消息
        await redis_manager.client.publish(command_channel, json.dumps(start_command))
        logger.info(f"已向 '{command_channel}' 发布启动命令: {start_command}")

        # 4. 等待爬虫执行（模拟或真实）
        # 在这个架构中，爬虫是独立进程，API服务无法直接知道它何时结束。
        # 因此，这里的模拟等待可以保留，或者你可以设计一个更复杂的状态轮询机制。
        # 但对于启动流程来说，发布命令这一步已经完成了它的使命。
        await asyncio.sleep(2) # 模拟耗时操作
        
        # 5. (可选) 模拟任务完成状态更新
        # 注意：在真实场景中，应由爬虫进程在结束时更新此状态。
        task_info = await redis_manager.get_task_info(task_id) # 重新获取最新的任务信息
        if task_info and task_info["status"] == "running": # 确保任务没有被取消
            task_info["status"] = "completed"
            task_info["completed_at"] = datetime.now().isoformat()
            await redis_manager.set_task_info(task_id, task_info)
            
            await redis_manager.publish_notification({
                "type": "task_completed",
                "task_id": task_id,
                "spider_name": spider_name,
                "timestamp": datetime.now().isoformat()
            })
        
        logger.info(f"爬虫任务处理完成: {task_id}")
            
    except Exception as e:
        # 如果函数内部任何一步出错，都会被这个except捕获
        logger.error(f"处理爬虫任务失败: {task_id}, 错误: {e}", exc_info=True)
        
        # 即使失败，也尝试更新任务状态为 failed
        try:
            task_info = await redis_manager.get_task_info(task_id)
            if task_info:
                task_info["status"] = "failed"
                task_info["error"] = str(e)
                task_info["completed_at"] = datetime.now().isoformat()
                await redis_manager.set_task_info(task_id, task_info)
                
                await redis_manager.publish_notification({
                    "type": "task_failed",
                    "task_id": task_id,
                    "spider_name": spider_name,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        except Exception as update_e:
            logger.error(f"更新失败任务状态时再次出错: {update_e}", exc_info=True)