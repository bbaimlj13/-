"""
随机User-Agent中间件
为每个请求随机设置User-Agent，防止被屏蔽
"""
import scrapy
from scrapy.http import HtmlResponse
from scrapy.utils.python import to_bytes
import random
import logging
from scrapy import signals

# 添加项目路径
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from shared.constants import USER_AGENTS

logger = logging.getLogger(__name__)

class RandomUserAgentMiddleware:
    """随机User-Agent中间件"""
    
    def __init__(self):
        self.user_agents = USER_AGENTS
    
    @classmethod
    def from_crawler(cls, crawler):
        """从爬虫创建中间件实例"""
        middleware = cls()
        crawler.signals.connect(middleware.spider_opened, signal=scrapy.signals.spider_opened)
        return middleware
    
    def spider_opened(self, spider):
        """爬虫打开时记录日志"""
        spider.logger.info(f"使用随机User-Agent中间件，共 {len(self.user_agents)} 个User-Agent")
    
    def process_request(self, request, spider):
        """处理请求，设置随机User-Agent"""
        if request.headers.get('User-Agent'):
            spider.logger.debug(f"请求已有User-Agent: {request.headers.get('User-Agent')}")
        else:
            user_agent = random.choice(self.user_agents)
            request.headers['User-Agent'] = user_agent
            spider.logger.debug(f"设置随机User-Agent: {user_agent[:50]}...")
        
        return None
    
    def process_response(self, request, response, spider):
        """处理响应"""
        return response
    
    def process_exception(self, request, exception, spider):
        """处理异常"""
        return None