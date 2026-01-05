import scrapy
from scrapy_redis.spiders import RedisSpider
from scrapy_redis import connection
from scrapy_project.items import NewsItem
import json
from urllib.parse import urljoin
import re
from shared.constants import NEWS_TYPE_ID_MAP, CATEGORY_MATCH_KEYWORDS
import redis
def get_news_type_id(title, content):
    """根据新闻标题和内容匹配分类"""
    if not title or not content:
        return NEWS_TYPE_ID_MAP["政策"]
    
    full_text = (title + " " + content).lower()
    
    for category, keywords in CATEGORY_MATCH_KEYWORDS.items():
        for kw in keywords:
            if kw in full_text:
                return NEWS_TYPE_ID_MAP[category]
    
    return NEWS_TYPE_ID_MAP["政策"]

class BjxSpider(RedisSpider):
    name = 'bjx_spider'
    allowed_domains = ['www.bjx.com.cn']
    redis_key = 'bjx:start_urls'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # ======================= 关键修改在这里 =======================
        # 手动创建 Redis 连接，指定 Docker 服务名作为主机
        redis_client = redis.Redis(host='news_crawler_redis', port=6379, password='123456')
        # ============================================================

        # 从Redis获取配置
        config_str = redis_client.get('config:bjx')
        if config_str:
            self.config = json.loads(config_str)
        else:
            self.config = {
                'urls': [
                    "https://www.bjx.com.cn/",
                    "https://guangfu.bjx.com.cn/",
                    "https://fd.bjx.com.cn/"
                ],
                'max_pages': 5,
                'rate_limit': 2
            }
    
    def parse(self, response):
        # 提取列表页链接 - 根据网站结构调整XPath
        articles = response.xpath('//div[contains(@class, "list")]//li/a')
        for article in articles:
            url = article.xpath('./@href').get()
            if url:
                full_url = urljoin(response.url, url)
                yield scrapy.Request(
                    full_url,
                    callback=self.parse_article,
                    meta={'source': 'bjx'}
                )
        
        # 翻页逻辑
        next_page = response.xpath('//a[contains(text(),"下一页")]/@href').get()
        if next_page:
            yield scrapy.Request(urljoin(response.url, next_page))
    
    def parse_article(self, response):
        """解析文章详情页"""
        item = NewsItem()
        
        # 提取标题
        title = response.xpath('//h1[@class="title"]/text()').get()
        if not title:
            title = response.xpath('//h1/text()').get()
        
        item['title'] = title.strip() if title else ''
        
        # 提取内容
        content_elements = response.xpath('//div[@class="content"]//text()').getall()
        if not content_elements:
            content_elements = response.xpath('//div[contains(@class, "article-content")]//text()').getall()
        
        content = ' '.join([text.strip() for text in content_elements if text.strip()])
        item['content'] = content
        
        # 分类
        new_type_id = get_news_type_id(item['title'], content)
        item['new_type'] = new_type_id
        
        # 来源
        item['source'] = response.meta.get('source', 'bjx')
        
        # 原始URL
        item['original_url'] = response.url
        
        # 新闻日期
        date_elem = response.xpath('//span[@class="time"]/text()').get()
        if date_elem:
            # 提取日期部分
            date_match = re.search(r'(\d{4}-\d{1,2}-\d{1,2})', date_elem)
            if date_match:
                item['news_date'] = date_match.group(1)
        
        # 图片
        images = response.xpath('//div[@class="content"]//img/@src').getall()
        if not images:
            images = response.xpath('//div[contains(@class, "article-content")]//img/@src').getall()
        
        item['images'] = [urljoin(response.url, img) for img in images if img]
        
        # 附件
        attachments = response.xpath('//a[contains(@href, ".pdf") or contains(@href, ".doc")]/@href').getall()
        item['attachments'] = [urljoin(response.url, att) for att in attachments if att]
        
        # 布局
        layout_elem = response.xpath('//div[@class="content"]').get()
        if not layout_elem:
            layout_elem = response.xpath('//div[contains(@class, "article-content")]').get()
        
        item['layout'] = layout_elem if layout_elem else ''
        
        # 权威性
        item['is_authoritative'] = True
        
        yield item
