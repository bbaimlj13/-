"""
常量定义
包含系统用到的所有常量
"""

from typing import Dict, List, Tuple
from datetime import timedelta

# ==================== 新闻相关常量 ====================

# 新闻类型ID映射
NEWS_TYPE_ID_MAP: Dict[str, int] = {
    "政策": 41,
    "天气": 42,
    "电力行业": 43
}

# 分类专属匹配关键词
CATEGORY_MATCH_KEYWORDS: Dict[str, List[str]] = {
    "政策": [
        "政策", "法规", "通知", "办法", "条例", "发改委", "能源局", 
        "文件", "规定", "公告", "指导意见", "批复", "规划", "国务院",
        "办公厅", "财政部", "工信部", "环保部", "住建部"
    ],
    "天气": [
        "高温", "低温", "暴雨", "暴雪", "大风", "雷电", "干旱", "洪涝", 
        "台风", "寒潮", "沙尘", "雾霾", "气象预警", "气候异常", 
        "中央气象台", "天气公报", "气象预报", "气象监测", "天气预报",
        "气候预测", "气象灾害", "气象服务", "气象数据"
    ],
    "电力行业": [
        "电力", "发电", "电网", "光伏", "风电", "水电", "储能", "输电", 
        "配电", "新能源", "煤炭", "天然气", "特高压", "变电站", "火电",
        "核电", "生物质", "智能电网", "微电网", "电力市场", "电价",
        "电力交易", "电力改革", "能源互联网", "充电桩"
    ]
}

# 目标天气网站URL
TARGET_URLS: List[Dict[str, str]] = [
    {"title_alias": "每日天气预报", "url": "https://www.nmc.cn/publish/weatherperday/index.htm"},
    {"title_alias": "大风预警", "url": "https://www.nmc.cn/publish/country/warning/wind.html"},
    {"title_alias": "天气新闻", "url": "https://www.nmc.cn/publish/news/weather_new.html"},
    {"title_alias": "环境气象公报", "url": "https://www.nmc.cn/publish/observations/environmental.html"},
    {"title_alias": "交通气象", "url": "https://www.nmc.cn/publish/traffic.html"},
    {"title_alias": "森林火险气象等级预报", "url": "https://www.nmc.cn/publish/environment/forestfire-doc.html"},
    {"title_alias": "草原火险气象等级预报", "url": "https://www.nmc.cn/publish/environment/glassland-fire.html"},
    {"title_alias": "空间天气公报", "url": "https://www.nmc.cn/publish/bulletin/swpc.html"},
    {"title_alias": "山洪灾害气象预警", "url": "https://www.nmc.cn/publish/mountainflood.html"},
    {"title_alias": "地质灾害气象风险预警", "url": "https://www.nmc.cn/publish/geohazard.html"},
    {"title_alias": "中小河流洪水气象预警", "url": "https://www.nmc.cn/publish/swdz/zxhlhsqxyj.html"},
    {"title_alias": "城市内涝气象风险预警", "url": "https://www.nmc.cn/publish/waterlogging.html"},
    {"title_alias": "全国大气环境公报", "url": "https://www.nmc.cn/publish/environment/National-Bulletin-atmospheric-environment.htm"}
]

# 关键词列表
KEYWORDS: List[str] = [
    # 天气相关
    "高温", "低温", "暴雨", "暴雪", "大风", "雷电", "干旱", "洪涝", "台风", "寒潮", "沙尘", "雾霾",
    "气象灾害预警", "极端天气事件", "气候异常", "气象条件变化", "气象因素影响",
    "中央气象台", "天气公报", "气象预报", "气象监测",
    
    # 能源相关
    "煤炭", "天然气", "石油", "水力", "太阳能", "风能", "水能", "生物质能", "地热能", "海洋能", "氢能",
    "煤炭价格", "天然气价格", "电力价格", "新能源补贴政策", "能源成本波动",
    
    # 发电相关
    "火力发电", "水力发电", "风力发电", "光伏发电", "核能发电", "生物质发电",
    "发电机组", "光伏组件", "风电机组", "变压器", "储能设备",
    "发电量", "发电效率", "发电成本", "发电可靠性",
    
    # 输电相关
    "高压输电线路", "特高压输电线路", "输电走廊", "电缆隧道",
    "变电站", "变压器", "开关设备", "互感器",
    "输电损耗率", "无功补偿", "电压稳定性",
    
    # 配电相关
    "配电网", "分布式电源", "微电网", "智能电网",
    "配电箱", "配电柜", "配电变压器", "断路器",
    "停电时间", "停电次数", "供电可靠性指标",
    
    # 用电相关
    "用电负荷", "高峰负荷", "低谷负荷", "负荷预测", "负荷特性",
    "工业用电", "商业用电", "居民用电", "农业用电",
    "节能减排", "能效提升", "需求侧管理", "智能用电",
    
    # 市场相关
    "电力现货交易", "电力期货交易", "电力中长期交易", "辅助服务市场交易",
    "电力市场价格", "交易电价", "结算电价",
    "发电企业", "售电公司", "电力用户", "电网企业",
    
    # 政策相关
    "电力体制改革", "能源发展规划", "新能源产业政策", "节能减排政策",
    "电力项目建设", "新能源装机容量", "电网改造升级", "电力市场动态", "电力市场交易",
    
    # 其他
    "新能源", "可再生能源", "清洁能源", "低碳发展", "碳中和", "碳达峰"
]

# ==================== HTTP相关常量 ====================

# HTTP状态码
HTTP_STATUS: Dict[int, str] = {
    200: "OK",
    201: "Created",
    202: "Accepted",
    204: "No Content",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout"
}

# HTTP方法
HTTP_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]

# HTTP请求头常量
HTTP_HEADERS: Dict[str, str] = {
    "USER_AGENT": "User-Agent",
    "CONTENT_TYPE": "Content-Type",
    "ACCEPT": "Accept",
    "AUTHORIZATION": "Authorization",
    "REFERER": "Referer",
    "COOKIE": "Cookie"
}

# HTTP Content-Type
CONTENT_TYPES: Dict[str, str] = {
    "JSON": "application/json",
    "FORM": "application/x-www-form-urlencoded",
    "MULTIPART": "multipart/form-data",
    "HTML": "text/html",
    "XML": "application/xml",
    "TEXT": "text/plain"
}

# ==================== Redis相关常量 ====================

# Redis键前缀
REDIS_KEY_PREFIXES: Dict[str, str] = {
    "TASK": "task:",              # 任务信息
    "QUEUE": "queue:",            # 任务队列
    "STATS": "stats:",            # 统计数据
    "SPIDER": "spider:",          # 爬虫状态
    "NODE": "node:",              # 节点信息
    "LOG": "log:",                # 系统日志
    "ALERT": "alert:",            # 系统警报
    "METRIC": "metric:",          # 性能指标
    "DUPE_FILTER": "dupefilter:", # 去重过滤器
    "LOCK": "lock:",              # 分布式锁
    "CONFIG": "config:"           # 配置信息
}

# Redis键模板
REDIS_KEYS: Dict[str, str] = {
    # 任务相关
    "TASK_INFO": "task:{task_id}",                    # 任务信息
    "TASK_STATS": "task_stats:{task_id}",             # 任务统计
    "TASK_ITEMS": "task_items:{task_id}",             # 任务项目
    "TASK_ERRORS": "task_errors:{task_id}",           # 任务错误
    
    # 队列相关
    "SPIDER_QUEUE": "{spider_name}:start_urls",       # 爬虫URL队列
    "PRIORITY_QUEUE": "priority_queue",               # 优先级队列
    
    # 爬虫相关
    "SPIDER_STATS": "spider_stats:{spider_name}",     # 爬虫统计
    "SPIDER_NODES": "spider_nodes:{spider_name}",     # 爬虫节点
    "SPIDER_STATUS": "spider:{spider_name}:status",   # 爬虫状态
    
    # 节点相关
    "NODE_INFO": "node:{node_id}:info",               # 节点信息
    "NODE_HEARTBEAT": "node:{node_id}:heartbeat",     # 节点心跳
    "NODE_SPIDERS": "node:{node_id}:spiders",         # 节点爬虫
    
    # 系统相关
    "NODE_SET": "crawler:nodes",
    "SYSTEM_STATS": "system:stats",                   # 系统统计
    "SYSTEM_LOGS": "system:logs",                     # 系统日志
    "SYSTEM_ALERTS": "system:alerts",                 # 系统警报
    "SYSTEM_CONFIG": "system:config",                 # 系统配置
    "SYSTEM_UPTIME": "system:uptime",                 # 系统运行时间
    
    # 去重相关
    "DUPE_FILTER": "{spider_name}:dupefilter",        # 去重集合
    
    # 分布式锁
    "LOCK_TASK": "lock:task:{task_id}",               # 任务锁
    "LOCK_SPIDER": "lock:spider:{spider_name}",       # 爬虫锁
    "LOCK_NODE": "lock:node:{node_id}",  
    # 命令和通知频道
    "CHANNEL_COMMANDS": "crawler:commands",           # 命令频道
    "CHANNEL_NODE_STATUS": "crawler:node_status",     # 节点状态频道
    "CHANNEL_SPIDER_STATUS": "crawler:spider_status", # 爬虫状态频道
    "CHANNEL_RESPONSES": "crawler:responses",         # 响应频道            
}

# Redis过期时间（秒）
REDIS_EXPIRE_TIMES: Dict[str, int] = {
    "TASK_INFO": 86400 * 7,          # 7天
    "TASK_STATS": 86400 * 30,        # 30天
    "NODE_HEARTBEAT": 300,           # 5分钟
    "NODE_INFO": 3600,               # 1小时
    "SPIDER_STATUS": 1800,           # 30分钟
    "LOCK": 60,                      # 60秒
    "CACHE_SHORT": 300,              # 5分钟
    "CACHE_MEDIUM": 3600,            # 1小时
    "CACHE_LONG": 86400,             # 1天
}

# ==================== 爬虫相关常量 ====================

# User-Agent列表
USER_AGENTS: List[str] = [
    # Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    
    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    
    # 移动端
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
]

# 爬虫配置默认值
CRAWLER_DEFAULTS: Dict[str, any] = {
    "CONCURRENT_REQUESTS": 8,
    "DOWNLOAD_DELAY": 1.0,
    "AUTOTHROTTLE_ENABLED": True,
    "AUTOTHROTTLE_START_DELAY": 1.0,
    "AUTOTHROTTLE_MAX_DELAY": 60.0,
    "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
    "RETRY_ENABLED": True,
    "RETRY_TIMES": 2,
    "RETRY_HTTP_CODES": [500, 502, 503, 504, 522, 524, 408, 429],
    "COOKIES_ENABLED": False,
    "TELNETCONSOLE_ENABLED": False,
    "LOG_LEVEL": "INFO",
    "DEPTH_LIMIT": 3,
    "CLOSESPIDER_TIMEOUT": 0,
    "CLOSESPIDER_PAGECOUNT": 0,
    "CLOSESPIDER_ITEMCOUNT": 1000,
    "CLOSESPIDER_ERRORCOUNT": 10,
}

# 支持的目标网站
SUPPORTED_WEBSITES: Dict[str, Dict[str, any]] = {
    "bjx": {
        "name": "北极星电力网",
        "domain": "bjx.com.cn",
        "description": "电力行业新闻资讯",
        "categories": ["电力行业"],
        "start_urls": ["https://www.bjx.com.cn/"],
        "rate_limit": 1.0
    },
    "nmc": {
        "name": "中央气象台",
        "domain": "nmc.cn",
        "description": "气象预报和预警信息",
        "categories": ["天气"],
        "start_urls": ["https://www.nmc.cn/"],
        "rate_limit": 2.0
    },
    "ndrc": {
        "name": "国家发改委",
        "domain": "ndrc.gov.cn",
        "description": "能源政策文件",
        "categories": ["政策"],
        "start_urls": ["https://www.ndrc.gov.cn/xxgk/jd/jd/"],
        "rate_limit": 3.0
    },
    "nea": {
        "name": "国家能源局",
        "domain": "nea.gov.cn",
        "description": "能源行业新闻",
        "categories": ["政策", "电力行业"],
        "start_urls": ["https://www.nea.gov.cn/"],
        "rate_limit": 2.0
    },
    "cres": {
        "name": "可再生能源学会",
        "domain": "cres.org.cn",
        "description": "可再生能源动态",
        "categories": ["电力行业"],
        "start_urls": ["http://www.cres.org.cn/"],
        "rate_limit": 3.0
    },
    "cec": {
        "name": "中电联",
        "domain": "cec.org.cn",
        "description": "电力行业报告和数据",
        "categories": ["电力行业"],
        "start_urls": ["https://www.cec.org.cn/"],
        "rate_limit": 2.0
    }
}

# ==================== 系统配置常量 ====================

# 默认配置值
DEFAULT_CONFIG: Dict[str, any] = {
    # API配置
    "API_HOST": "0.0.0.0",
    "API_PORT": 8000,
    "API_WORKERS": 4,
    "API_RELOAD": True,
    
    # 日志配置
    "LOG_LEVEL": "INFO",
    "LOG_FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "LOG_FILE": "logs/api_server.log",
    "LOG_MAX_SIZE": 10485760,  # 10MB
    "LOG_BACKUP_COUNT": 10,
    
    # 数据库配置
    "MYSQL_POOL_SIZE": 10,
    "MYSQL_MAX_OVERFLOW": 20,
    "MYSQL_POOL_RECYCLE": 3600,
    
    # Redis配置
    "REDIS_POOL_SIZE": 20,
    "REDIS_MAX_CONNECTIONS": 100,
    "REDIS_SOCKET_TIMEOUT": 5,
    
    # 监控配置
    "MONITOR_INTERVAL": 2.0,  # 监控间隔（秒）
    "METRIC_RETENTION_DAYS": 30,  # 指标保留天数
    "ALERT_RETENTION_DAYS": 90,  # 警报保留天数
    "LOG_RETENTION_DAYS": 30,  # 日志保留天数
    
    # 任务配置
    "TASK_TIMEOUT": 3600,  # 任务超时时间（秒）
    "TASK_MAX_RETRIES": 3,  # 任务最大重试次数
    "TASK_PRIORITY_DEFAULT": 5,  # 默认优先级
    
    # 爬虫配置
    "CRAWLER_HEARTBEAT_INTERVAL": 30,  # 爬虫心跳间隔（秒）
    "CRAWLER_TIMEOUT": 300,  # 爬虫超时时间（秒）
    "CRAWLER_MAX_CONCURRENT": 10,  # 最大并发爬虫数
}

# 时间间隔常量（秒）
TIME_INTERVALS: Dict[str, int] = {
    "SECOND": 1,
    "MINUTE": 60,
    "HOUR": 3600,
    "DAY": 86400,
    "WEEK": 604800,
    "MONTH": 2592000,
    "YEAR": 31536000
}

# 日期时间格式
DATETIME_FORMATS: Dict[str, str] = {
    "DATETIME": "%Y-%m-%d %H:%M:%S",
    "DATE": "%Y-%m-%d",
    "TIME": "%H:%M:%S",
    "ISO": "%Y-%m-%dT%H:%M:%S",
    "COMPACT": "%Y%m%d%H%M%S",
    "FILE": "%Y%m%d_%H%M%S"
}

# ==================== 错误码常量 ====================

# 系统错误码
ERROR_CODES: Dict[int, str] = {
    # 通用错误 (1000-1999)
    1000: "成功",
    1001: "系统错误",
    1002: "参数错误",
    1003: "资源不存在",
    1004: "权限不足",
    1005: "请求超时",
    1006: "服务不可用",
    1007: "数据库错误",
    1008: "网络错误",
    1009: "配置错误",
    
    # 爬虫相关错误 (2000-2999)
    2000: "爬虫任务创建失败",
    2001: "爬虫任务不存在",
    2002: "爬虫任务已存在",
    2003: "爬虫配置错误",
    2004: "爬虫执行失败",
    2005: "爬虫解析失败",
    2006: "爬虫存储失败",
    2007: "爬虫超时",
    2008: "爬虫被拒绝",
    2009: "爬虫URL无效",
    
    # 节点相关错误 (3000-3999)
    3000: "节点注册失败",
    3001: "节点不存在",
    3002: "节点心跳超时",
    3003: "节点状态异常",
    3004: "节点资源不足",
    3005: "节点通信失败",
    
    # 队列相关错误 (4000-4999)
    4000: "队列已满",
    4001: "队列为空",
    4002: "队列操作失败",
    4003: "队列锁定失败",
    4004: "队列超时",
    
    # 数据相关错误 (5000-5999)
    5000: "数据验证失败",
    5001: "数据存储失败",
    5002: "数据查询失败",
    5003: "数据更新失败",
    5004: "数据删除失败",
    5005: "数据重复",
    5006: "数据格式错误",
}

# ==================== 导出常量 ====================

__all__ = [
    # 新闻相关
    'NEWS_TYPE_ID_MAP',
    'CATEGORY_MATCH_KEYWORDS',
    'TARGET_URLS',
    'KEYWORDS',
    
    # HTTP相关
    'HTTP_STATUS',
    'HTTP_METHODS',
    'HTTP_HEADERS',
    'CONTENT_TYPES',
    
    # Redis相关
    'REDIS_KEY_PREFIXES',
    'REDIS_KEYS',
    'REDIS_EXPIRE_TIMES',
    
    # 爬虫相关
    'USER_AGENTS',
    'CRAWLER_DEFAULTS',
    'SUPPORTED_WEBSITES',
    'TASK_PRIORITIES',          # 新增
    'TASK_STATUS_FLOW',         # 新增
    
    # 系统配置
    'DEFAULT_CONFIG',
    'TIME_INTERVALS',
    'DATETIME_FORMATS',
    'FILE_CONSTANTS',           # 新增
    
    # 错误码
    'ERROR_CODES',
]