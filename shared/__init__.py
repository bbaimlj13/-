"""
共享模块
包含配置、模型和常量等共享代码
"""

from .config import Config
from .models import NewsItem, CrawlerTask, SystemStats, NewsCategory
from .constants import (
    NEWS_TYPE_ID_MAP,
    CATEGORY_MATCH_KEYWORDS,
    TARGET_URLS,
    KEYWORDS,
    USER_AGENTS,
    REDIS_KEYS,
    HTTP_STATUS
)

__version__ = '2.0.0'
__author__ = '分布式新闻爬虫系统'

__all__ = [
    'Config',
    'NewsItem',
    'CrawlerTask',
    'SystemStats',
    'NewsCategory',
    'NEWS_TYPE_ID_MAP',
    'CATEGORY_MATCH_KEYWORDS',
    'TARGET_URLS',
    'KEYWORDS',
    'USER_AGENTS',
    'REDIS_KEYS',
    'HTTP_STATUS'
]