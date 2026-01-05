import scrapy
from scrapy_redis.spiders import RedisSpider
from scrapy_project.items import NewsItem
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

class FgwSpider(RedisSpider):
    name = 'fgw_spider'
    redis_key = 'fgw_spider:start_urls'
    
    def parse(self, response):
        # 发改委列表页解析
        articles = response.xpath('//div[@class="list"]//li/a')
        for article in articles:
            url = article.xpath('./@href').get()
            if url:
                full_url = urljoin(response.url, url)
                yield scrapy.Request(
                    full_url,
                    callback=self.parse_article,
                    meta={'source': 'fgw'}
                )
        
        # 翻页
        next_page = response.xpath('//a[contains(text(),"下一页")]/@href').get()
        if next_page:
            yield scrapy.Request(urljoin(response.url, next_page))
    
    def parse_article(self, response):
        """解析文章详情页"""
        item = NewsItem()
        
        # 标题
        title = response.xpath('//h1[@class="title"]/text()').get()
        if not title:
            title = response.xpath('//h1/text()').get()
        
        item['title'] = title.strip() if title else ''
        
        # 内容
        content_elements = response.xpath('//div[@class="TRS_Editor"]//text()').getall()
        if not content_elements:
            content_elements = response.xpath('//div[@class="article-content"]//text()').getall()
        
        content = ' '.join([text.strip() for text in content_elements if text.strip()])
        item['content'] = content
        
        # 分类
        new_type_id = get_news_type_id(item['title'], content)
        item['new_type'] = new_type_id
        
        # 来源
        item['source'] = response.meta.get('source', 'fgw')
        
        # 原始URL
        item['original_url'] = response.url
        
        # 日期
        date_elem = response.xpath('//div[@class="article-info"]/span[1]/text()').get()
        if date_elem:
            date_match = re.search(r'(\d{4}-\d{1,2}-\d{1,2})', date_elem)
            if date_match:
                item['news_date'] = date_match.group(1)
        
        # 图片
        images = response.xpath('//div[@class="TRS_Editor"]//img/@src').getall()
        if not images:
            images = response.xpath('//div[@class="article-content"]//img/@src').getall()
        
        item['images'] = [urljoin(response.url, img) for img in images if img]
        
        # 附件
        attachments = response.xpath('//a[contains(@href, ".pdf") or contains(@href, ".doc")]/@href').getall()
        item['attachments'] = [urljoin(response.url, att) for att in attachments if att]
        
        # 布局
        layout_elem = response.xpath('//div[@class="TRS_Editor"]').get()
        if not layout_elem:
            layout_elem = response.xpath('//div[@class="article-content"]').get()
        
        item['layout'] = layout_elem if layout_elem else ''
        
        # 权威性
        item['is_authoritative'] = True
        
        yield item