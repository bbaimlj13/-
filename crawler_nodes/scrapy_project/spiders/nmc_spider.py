import scrapy
from scrapy_redis.spiders import RedisSpider
from scrapy_project.items import NewsItem
from urllib.parse import urljoin
import re
from shared.constants import TARGET_URLS, NEWS_TYPE_ID_MAP
import redis
class NmcSpider(RedisSpider):
    name = 'nmc_spider'
    redis_key = 'nmc_spider:start_urls'
    
    def parse(self, response):
        # 中央气象台的页面直接提取内容
        item = NewsItem()
        
        # 标题
        title_alias = ''
        for target in TARGET_URLS:
            if target['url'] == response.url:
                title_alias = target['title_alias']
                break
        
        page_title = response.xpath('//title/text()').get('').strip()
        item['title'] = title_alias if title_alias else page_title
        if not item['title']:
            item['title'] = "中央气象台天气信息"
        
        # 内容
        content_elements = response.xpath('//div[@class="content"]//text()').getall()
        if not content_elements:
            content_elements = response.xpath('//div[contains(@class, "main")]//text()').getall()
        
        content = ' '.join([text.strip() for text in content_elements if text.strip()])
        item['content'] = content
        
        # 分类
        item['new_type'] = NEWS_TYPE_ID_MAP["天气"]
        
        # 来源
        item['source'] = "中央气象台"
        
        # 原始URL
        item['original_url'] = response.url
        
        # 日期
        date_elem = response.xpath('//div[contains(text(), "发布时间")]/text()').get()
        if date_elem:
            date_match = re.search(r'(\d{4}-\d{1,2}-\d{1,2})', date_elem)
            if date_match:
                item['news_date'] = date_match.group(1)
        
        # 图片
        images = response.xpath('//div[@class="content"]//img/@src').getall()
        if not images:
            images = response.xpath('//div[contains(@class, "main")]//img/@src').getall()
        
        item['images'] = [urljoin(response.url, img) for img in images if img]
        
        # 布局
        layout_elem = response.xpath('//div[@class="content"]').get()
        if not layout_elem:
            layout_elem = response.xpath('//div[contains(@class, "main")]').get()
        
        item['layout'] = layout_elem if layout_elem else ''
        
        # 权威性
        item['is_authoritative'] = True
        
        yield item