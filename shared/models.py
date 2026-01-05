"""
数据模型定义
包含系统用到的所有Pydantic模型
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class NewsCategory(str, Enum):
    """新闻分类枚举"""
    POLICY = "policy"  # 政策
    WEATHER = "weather"  # 天气
    POWER = "power"  # 电力行业


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SpiderStatus(str, Enum):
    """爬虫状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class LogLevel(str, Enum):
    """日志级别枚举"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertSeverity(str, Enum):
    """警报严重程度枚举"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NewsItem(BaseModel):
    """新闻数据模型"""
    id: Optional[str] = Field(None, description="新闻ID")
    title: str = Field(..., description="标题", min_length=1, max_length=500)
    content: str = Field(..., description="内容", min_length=1)
    summary: Optional[str] = Field(None, description="摘要", max_length=1000)
    source: str = Field(..., description="来源", max_length=200)
    original_url: str = Field(..., description="原始URL", max_length=500)
    news_date: Optional[str] = Field(None, description="新闻日期")
    publish_time: Optional[datetime] = Field(None, description="发布时间")
    images: List[str] = Field(default_factory=list, description="图片URL列表")
    attachments: List[str] = Field(default_factory=list, description="附件列表")
    layout: Optional[str] = Field(None, description="HTML布局")
    category: Optional[NewsCategory] = Field(None, description="新闻分类")
    new_type: Optional[int] = Field(None, description="新闻类型ID", ge=1)
    keywords: List[str] = Field(default_factory=list, description="关键词列表")
    author: Optional[str] = Field(None, description="作者", max_length=100)
    is_authoritative: bool = Field(default=True, description="是否权威来源")
    is_top: bool = Field(default=False, description="是否置顶")
    view_count: int = Field(default=0, description="浏览量", ge=0)
    like_count: int = Field(default=0, description="点赞数", ge=0)
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    
    @validator('original_url')
    def validate_url(cls, v):
        """验证URL格式"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL必须以http://或https://开头')
        return v
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S'),
        }


class CrawlerTask(BaseModel):
    """爬虫任务模型"""
    task_id: str = Field(..., description="任务ID")
    spider_name: str = Field(..., description="爬虫名称")
    urls: List[str] = Field(..., description="起始URL列表", min_items=1)
    config: Dict[str, Any] = Field(default_factory=dict, description="爬虫配置")
    priority: int = Field(default=5, description="优先级(1-10)", ge=1, le=10)
    max_items: Optional[int] = Field(default=100, description="最大抓取数量", ge=1)
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    paused_at: Optional[datetime] = Field(None, description="暂停时间")
    resumed_at: Optional[datetime] = Field(None, description="恢复时间")
    cancelled_at: Optional[datetime] = Field(None, description="取消时间")
    error: Optional[str] = Field(None, description="错误信息")
    total_items: int = Field(default=0, description="总项目数", ge=0)
    processed_items: int = Field(default=0, description="已处理项目数", ge=0)
    failed_items: int = Field(default=0, description="失败项目数", ge=0)
    progress: float = Field(default=0.0, description="进度百分比", ge=0.0, le=100.0)
    node_id: Optional[str] = Field(None, description="执行节点ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    
    @validator('urls')
    def validate_urls(cls, v):
        """验证URL列表"""
        validated_urls = []
        for url in v:
            if not url.startswith(('http://', 'https://')):
                raise ValueError(f'URL必须以http://或https://开头: {url}')
            validated_urls.append(url)
        return validated_urls
    
    class Config:
        from_attributes = True


class SystemStats(BaseModel):
    """系统统计模型"""
    crawler_nodes: int = Field(default=0, description="爬虫节点数", ge=0)
    active_spiders: int = Field(default=0, description="活跃爬虫数", ge=0)
    total_tasks: int = Field(default=0, description="总任务数", ge=0)
    running_tasks: int = Field(default=0, description="运行中任务数", ge=0)
    completed_tasks: int = Field(default=0, description="已完成任务数", ge=0)
    failed_tasks: int = Field(default=0, description="失败任务数", ge=0)
    queue_size: int = Field(default=0, description="队列大小", ge=0)
    items_processed: int = Field(default=0, description="已处理新闻数", ge=0)
    items_failed: int = Field(default=0, description="失败新闻数", ge=0)
    processing_rate: float = Field(default=0.0, description="处理速率(个/分钟)", ge=0.0)
    uptime: float = Field(default=0.0, description="系统运行时间(小时)", ge=0.0)
    cpu_usage: float = Field(default=0.0, description="CPU使用率(%)", ge=0.0, le=100.0)
    memory_usage: float = Field(default=0.0, description="内存使用率(%)", ge=0.0, le=100.0)
    disk_usage: float = Field(default=0.0, description="磁盘使用率(%)", ge=0.0, le=100.0)
    timestamp: datetime = Field(default_factory=datetime.now, description="统计时间")
    
    class Config:
        from_attributes = True


class CrawlerNode(BaseModel):
    """爬虫节点模型"""
    node_id: str = Field(..., description="节点ID")
    hostname: str = Field(..., description="主机名")
    ip_address: str = Field(..., description="IP地址")
    status: SpiderStatus = Field(default=SpiderStatus.IDLE, description="节点状态")
    active_spiders: List[str] = Field(default_factory=list, description="活跃爬虫列表")
    cpu_usage: float = Field(default=0.0, description="CPU使用率(%)", ge=0.0, le=100.0)
    memory_usage: float = Field(default=0.0, description="内存使用率(%)", ge=0.0, le=100.0)
    items_processed: int = Field(default=0, description="处理项目数", ge=0)
    items_failed: int = Field(default=0, description="失败项目数", ge=0)
    last_heartbeat: Optional[datetime] = Field(None, description="最后心跳时间")
    started_at: datetime = Field(default_factory=datetime.now, description="启动时间")
    uptime: float = Field(default=0.0, description="运行时间(小时)", ge=0.0)
    version: str = Field(default="1.0.0", description="节点版本")
    
    class Config:
        from_attributes = True


class SpiderStats(BaseModel):
    """爬虫统计模型"""
    spider_name: str = Field(..., description="爬虫名称")
    items_processed: int = Field(default=0, description="处理项目数", ge=0)
    items_failed: int = Field(default=0, description="失败项目数", ge=0)
    start_requests: int = Field(default=0, description="起始请求数", ge=0)
    response_received: int = Field(default=0, description="收到响应数", ge=0)
    response_failed: int = Field(default=0, description="失败响应数", ge=0)
    duplicates_filtered: int = Field(default=0, description="去重过滤数", ge=0)
    last_crawl_time: Optional[datetime] = Field(None, description="最后爬取时间")
    avg_response_time: float = Field(default=0.0, description="平均响应时间(秒)", ge=0.0)
    crawl_rate: float = Field(default=0.0, description="爬取速率(个/分钟)", ge=0.0)
    queue_size: int = Field(default=0, description="队列大小", ge=0)
    dupefilter_size: int = Field(default=0, description="去重集合大小", ge=0)
    
    class Config:
        from_attributes = True


class SystemLog(BaseModel):
    """系统日志模型"""
    id: str = Field(..., description="日志ID")
    timestamp: datetime = Field(..., description="日志时间")
    level: LogLevel = Field(..., description="日志级别")
    source: str = Field(..., description="日志来源")
    message: str = Field(..., description="日志消息")
    module: Optional[str] = Field(None, description="模块名称")
    function: Optional[str] = Field(None, description="函数名称")
    line_number: Optional[int] = Field(None, description="行号")
    extra_data: Dict[str, Any] = Field(default_factory=dict, description="额外数据")
    
    class Config:
        from_attributes = True


class SystemAlert(BaseModel):
    """系统警报模型"""
    id: str = Field(..., description="警报ID")
    timestamp: datetime = Field(..., description="警报时间")
    severity: AlertSeverity = Field(..., description="严重程度")
    source: str = Field(..., description="警报来源")
    message: str = Field(..., description="警报消息")
    details: Dict[str, Any] = Field(default_factory=dict, description="详细数据")
    acknowledged: bool = Field(default=False, description="是否已确认")
    acknowledged_by: Optional[str] = Field(None, description="确认人")
    acknowledged_at: Optional[datetime] = Field(None, description="确认时间")
    
    class Config:
        from_attributes = True


class PerformanceMetrics(BaseModel):
    """性能指标模型"""
    timestamp: datetime = Field(..., description="时间戳")
    cpu_usage: float = Field(..., description="CPU使用率(%)", ge=0.0, le=100.0)
    memory_usage: float = Field(..., description="内存使用率(%)", ge=0.0, le=100.0)
    disk_usage: float = Field(..., description="磁盘使用率(%)", ge=0.0, le=100.0)
    network_io: Dict[str, float] = Field(default_factory=dict, description="网络IO")
    active_connections: int = Field(default=0, description="活跃连接数", ge=0)
    queue_depth: int = Field(default=0, description="队列深度", ge=0)
    processing_latency: float = Field(default=0.0, description="处理延迟(秒)", ge=0.0)
    
    class Config:
        from_attributes = True


class DatabaseConnection(BaseModel):
    """数据库连接模型"""
    host: str = Field(..., description="主机地址")
    port: int = Field(..., description="端口号", ge=1, le=65535)
    database: str = Field(..., description="数据库名称")
    user: Optional[str] = Field(None, description="用户名")
    status: str = Field(..., description="连接状态")
    latency: float = Field(default=0.0, description="延迟(秒)", ge=0.0)
    last_check: datetime = Field(..., description="最后检查时间")
    
    class Config:
        from_attributes = True


# 简化的API请求/响应模型
class CreateTaskRequest(BaseModel):
    """创建任务请求模型"""
    spider_name: str = Field(..., description="爬虫名称")
    urls: List[str] = Field(..., description="起始URL列表", min_items=1)
    config: Dict[str, Any] = Field(default_factory=dict, description="爬虫配置")
    priority: int = Field(default=5, description="优先级(1-10)", ge=1, le=10)
    max_items: Optional[int] = Field(default=100, description="最大抓取数量", ge=1)


class TaskResponse(BaseModel):
    """任务响应模型"""
    task_id: str = Field(..., description="任务ID")
    spider_name: str = Field(..., description="爬虫名称")
    urls_count: int = Field(..., description="URL数量")
    status: str = Field(..., description="任务状态")
    created_at: datetime = Field(..., description="创建时间")
    queue_key: str = Field(..., description="Redis队列键")


# 导出所有模型
__all__ = [
    'NewsCategory',
    'TaskStatus',
    'SpiderStatus',
    'LogLevel',
    'AlertSeverity',
    'NewsItem',
    'CrawlerTask',
    'SystemStats',
    'CrawlerNode',
    'SpiderStats',
    'SystemLog',
    'SystemAlert',
    'PerformanceMetrics',
    'DatabaseConnection',
    'CreateTaskRequest',
    'TaskResponse'
]