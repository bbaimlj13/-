"""
Scrapy设置配置文件
适配分布式爬虫系统
"""

import os
import sys

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.config import Config
from shared.constants import USER_AGENTS, REDIS_KEYS

# Scrapy基本配置
BOT_NAME = 'power_news_crawler'

SPIDER_MODULES = ["spiders"]
NEWSPIDER_MODULE = "spiders"

# 用户代理
USER_AGENT = USER_AGENTS[0]

# 遵守robots.txt（根据网站要求调整）
ROBOTSTXT_OBEY = False

# 并发设置
CONCURRENT_REQUESTS = Config.CRAWLER_CONCURRENT_REQUESTS
CONCURRENT_REQUESTS_PER_DOMAIN = Config.CRAWLER_CONCURRENT_REQUESTS_PER_DOMAIN
CONCURRENT_REQUESTS_PER_IP = 2

# 下载延迟
DOWNLOAD_DELAY = Config.CRAWLER_DOWNLOAD_DELAY
RANDOMIZE_DOWNLOAD_DELAY = True

# Cookie启用
COOKIES_ENABLED = True
COOKIES_DEBUG = False

# Telnet控制台（用于调试）
TELNETCONSOLE_ENABLED = True
TELNETCONSOLE_PORT = [6023, 6073]
TELNETCONSOLE_HOST = '127.0.0.1'

# 重试设置
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]
RETRY_PRIORITY_ADJUST = -1

# 超时设置
DOWNLOAD_TIMEOUT = 30
DOWNLOAD_HANDLERS = {
    'http': 'scrapy.core.downloader.handlers.http.HTTPDownloadHandler',
    'https': 'scrapy.core.downloader.handlers.http.HTTPDownloadHandler',
}

# 自动限速
AUTOTHROTTLE_ENABLED = Config.CRAWLER_AUTOTHROTTLE_ENABLED
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = False

# 深度限制
DEPTH_LIMIT = 3
DEPTH_PRIORITY = 1
DEPTH_STATS_VERBOSE = True

# Scrapy-Redis配置
SCHEDULER = "scrapy_redis.scheduler.Scheduler"
SCHEDULER_PERSIST = True  # 保持队列不丢失
SCHEDULER_FLUSH_ON_START = False  # 启动时不清理队列
SCHEDULER_IDLE_BEFORE_CLOSE = 10  # 空闲多长时间后关闭

# 去重过滤器
DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"
DUPEFILTER_DEBUG = True

# Redis队列
SCHEDULER_QUEUE_CLASS = "scrapy_redis.queue.PriorityQueue"

# Redis连接
REDIS_URL = Config.get_redis_url()
REDIS_HOST = Config.REDIS_HOST
REDIS_PORT = Config.REDIS_PORT
REDIS_PARAMS = {
    'password': Config.REDIS_PASSWORD,
    'db': Config.REDIS_DB,
    'encoding': 'utf-8',
    'decode_responses': True,
}

# 管道配置
ITEM_PIPELINES = {
    'scrapy_project.pipelines.NewsValidationPipeline': 100,
    'scrapy_project.pipelines.DatabasePipeline': 200,
    'scrapy_project.pipelines.ImageUploadPipeline': 300,
    'scrapy_project.pipelines.AttachmentUploadPipeline': 400,
    'scrapy_project.pipelines.StatisticsPipeline': 500,
    'scrapy_redis.pipelines.RedisPipeline': 800,
}
# 中间件
DOWNLOADER_MIDDLEWARES = {
    # 默认中间件
    'scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware': 100,
    'scrapy.downloadermiddlewares.httpauth.HttpAuthMiddleware': 300,
    'scrapy.downloadermiddlewares.downloadtimeout.DownloadTimeoutMiddleware': 350,
    'scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware': 400,
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': 500,
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 550,
    'scrapy.downloadermiddlewares.ajaxcrawl.AjaxCrawlMiddleware': 560,
    'scrapy.downloadermiddlewares.redirect.MetaRefreshMiddleware': 580,
    'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 590,
    'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': 600,
    'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': 700,
    'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 750,
    'scrapy.downloadermiddlewares.stats.DownloaderStats': 850,
    'scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware': 900,
    
    # 自定义中间件
    'scrapy_project.middlewares.RandomUserAgentMiddleware': 450,
    'scrapy_project.middlewares.SeleniumMiddleware': 543,
}

# Spider中间件
SPIDER_MIDDLEWARES = {
    'scrapy.spidermiddlewares.httperror.HttpErrorMiddleware': 50,
    'scrapy.spidermiddlewares.offsite.OffsiteMiddleware': 500,
    'scrapy.spidermiddlewares.referer.RefererMiddleware': 700,
    'scrapy.spidermiddlewares.urllength.UrlLengthMiddleware': 800,
    'scrapy.spidermiddlewares.depth.DepthMiddleware': 900,
}

# 扩展
EXTENSIONS = {
    'scrapy.extensions.telnet.TelnetConsole': None,
    'scrapy.extensions.corestats.CoreStats': 0,
    'scrapy.extensions.memusage.MemoryUsage': 0,
    'scrapy.extensions.logstats.LogStats': 0,
    'scrapy.extensions.throttle.AutoThrottle': 0,
    'scrapy.extensions.closespider.CloseSpider': 0,
}

# 内存使用
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 1024  # 1GB内存限制
MEMUSAGE_WARNING_MB = 800
MEMUSAGE_NOTIFY_MAIL = []

# 自动关闭
CLOSESPIDER_TIMEOUT = 0  # 0表示不超时
CLOSESPIDER_PAGECOUNT = 0  # 0表示不限制页面数
CLOSESPIDER_ITEMCOUNT = 1000  # 抓取1000个项目后关闭
CLOSESPIDER_ERRORCOUNT = 50  # 发生50个错误后关闭

# HTTP缓存
HTTPCACHE_ENABLED = False
HTTPCACHE_EXPIRATION_SECS = 0
HTTPCACHE_DIR = 'httpcache'
HTTPCACHE_IGNORE_HTTP_CODES = [404, 403, 500]
HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

# 启用Ajax爬取
AJAXCRAWL_ENABLED = True

# 默认请求头
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0',
}

# 忽略的HTTP状态码
HTTPERROR_ALLOWED_CODES = [404, 403, 429, 503]

# 启用Feed导出
FEED_EXPORT_ENCODING = 'utf-8'
FEED_FORMAT = 'json'
FEED_URI = None  # 禁用文件导出，使用数据库

# 编码
FEED_EXPORT_ENCODING = 'utf-8'

# 日志配置
LOG_LEVEL = Config.LOG_LEVEL
LOG_FILE = None 
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
LOG_DATEFORMAT = '%Y-%m-%d %H:%M:%S'

# 爬虫自定义设置
CRAWLER_SETTINGS = {
    'MAX_PAGES_PER_SITE': 100,
    'MAX_DEPTH': 3,
    'RESPECT_ROBOTS_TXT': False,
    'DOWNLOAD_TIMEOUT': 30,
    'RETRY_TIMES': 3,
}

# 自定义配置
CUSTOM_SETTINGS = {
    # 图片处理
    'IMAGES_STORE': Config.MINIO_BUCKET,
    'IMAGES_URLS_FIELD': 'images',
    'IMAGES_RESULT_FIELD': 'images',
    
    # 文件下载
    'FILES_STORE': Config.MINIO_BUCKET,
    'FILES_URLS_FIELD': 'attachments',
    'FILES_RESULT_FIELD': 'attachments',
    
    # 数据库
    'MYSQL_HOST': Config.MYSQL_HOST,
    'MYSQL_PORT': Config.MYSQL_PORT,
    'MYSQL_USER': Config.MYSQL_USER,
    'MYSQL_PASSWORD': Config.MYSQL_PASSWORD,
    'MYSQL_DATABASE': Config.MYSQL_DATABASE,
    
    # MinIO
    'MINIO_ENDPOINT': Config.MINIO_ENDPOINT,
    'MINIO_ACCESS_KEY': Config.MINIO_ACCESS_KEY,
    'MINIO_SECRET_KEY': Config.MINIO_SECRET_KEY,
    'MINIO_BUCKET': Config.MINIO_BUCKET,
    'MINIO_SECURE': Config.MINIO_SECURE,
}

# 更新设置
globals().update(CUSTOM_SETTINGS)