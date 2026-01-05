"""
Scrapy Item定义
定义新闻数据的结构和字段
"""

import scrapy
from scrapy.loader import ItemLoader
from itemloaders.processors import TakeFirst, MapCompose, Join
import re
from datetime import datetime

def clean_text(text):
    """清理文本，移除多余空白字符"""
    if text is None:
        return ''
    
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', ' ', text)
    # 移除多余空白
    text = re.sub(r'\s+', ' ', text)
    # 移除前后空白
    text = text.strip()
    
    return text

def clean_date(date_str):
    """清理日期字符串"""
    if not date_str:
        return None
    
    try:
        # 常见日期格式匹配
        date_patterns = [
            r'(\d{4}-\d{1,2}-\d{1,2})',
            r'(\d{4}/\d{1,2}/\d{1,2})',
            r'(\d{4}年\d{1,2}月\d{1,2}日)',
            r'(\d{1,2}-\d{1,2}-\d{4})',
            r'(\d{1,2}/\d{1,2}/\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                date_str = match.group(1)
                break
        
        # 统一格式化为 YYYY-MM-DD
        date_str = re.sub(r'[年/]', '-', date_str)
        date_str = re.sub(r'月|日', '', date_str)
        
        # 尝试解析日期
        from datetime import datetime
        try:
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
            return parsed_date.strftime('%Y-%m-%d')
        except ValueError:
            # 尝试其他格式
            try:
                parsed_date = datetime.strptime(date_str, '%d-%m-%Y')
                return parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                return None
    
    except Exception:
        return None

def clean_url(url):
    """清理URL"""
    if not url:
        return ''
    
    # 确保URL是完整的
    if url.startswith('//'):
        return 'https:' + url
    elif url.startswith('/'):
        # 需要与基础URL结合，这里只清理，具体结合在spider中处理
        return url
    
    return url.strip()

def extract_summary(content, max_length=200):
    """从内容中提取摘要"""
    if not content:
        return ''
    
    # 移除HTML标签和多余空白
    clean_content = clean_text(content)
    
    # 截取前max_length个字符
    if len(clean_content) > max_length:
        summary = clean_content[:max_length] + '...'
    else:
        summary = clean_content
    
    return summary

class NewsItem(scrapy.Item):
    """
    新闻数据项
    对应数据库表 cns_news_data
    """
    
    # 基础字段
    title = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    content = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=Join(' ')
    )
    summary = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    
    # URL和来源
    original_url = scrapy.Field(
        input_processor=MapCompose(clean_url),
        output_processor=TakeFirst()
    )
    source = scrapy.Field(
        input_processor=MapCompose(clean_text),
        output_processor=TakeFirst()
    )
    
    # 日期和时间
    news_date = scrapy.Field(
        input_processor=MapCompose(clean_date),
        output_processor=TakeFirst()
    )
    create_time = scrapy.Field(
        output_processor=TakeFirst()
    )
    update_time = scrapy.Field(
        output_processor=TakeFirst()
    )
    
    # 媒体资源
    images = scrapy.Field(
        input_processor=MapCompose(clean_url)
    )
    attachments = scrapy.Field(
        input_processor=MapCompose(clean_url)
    )
    
    # 布局和格式
    layout = scrapy.Field(
        output_processor=TakeFirst()
    )
    
    # 分类和类型
    new_type = scrapy.Field(
        output_processor=TakeFirst()
    )
    topic_ids = scrapy.Field()
    
    # 权威性和重要性
    is_authoritative_source = scrapy.Field(
        output_processor=TakeFirst()
    )
    is_great = scrapy.Field(
        output_processor=TakeFirst()
    )
    
    # 管理字段
    create_by = scrapy.Field(
        output_processor=TakeFirst()
    )
    update_by = scrapy.Field(
        output_processor=TakeFirst()
    )
    
    # 爬虫信息
    spider_name = scrapy.Field(
        output_processor=TakeFirst()
    )
    node_id = scrapy.Field(
        output_processor=TakeFirst()
    )
    crawl_time = scrapy.Field(
        output_processor=TakeFirst()
    )

class NewsItemLoader(ItemLoader):
    """
    新闻项加载器
    提供便捷的方法来加载和处理新闻数据
    """
    
    default_item_class = NewsItem
    default_input_processor = MapCompose(clean_text)
    default_output_processor = TakeFirst()
    
    def add_summary_from_content(self):
        """从内容中提取摘要"""
        content = self.get_output_value('content')
        if content:
            summary = extract_summary(content)
            self.add_value('summary', summary)
    
    def add_current_time(self, field_name='create_time'):
        """添加当前时间"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.add_value(field_name, current_time)
    
    def add_spider_info(self, spider_name, node_id='unknown'):
        """添加爬虫信息"""
        self.add_value('spider_name', spider_name)
        self.add_value('node_id', node_id)
        self.add_value('crawl_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    def add_default_values(self):
        """添加默认值"""
        # 如果没有创建者，使用爬虫名称
        if not self.get_output_value('create_by'):
            spider_name = self.get_output_value('spider_name') or 'scrapy_crawler'
            self.add_value('create_by', spider_name)
        
        # 如果没有更新者，使用爬虫名称
        if not self.get_output_value('update_by'):
            spider_name = self.get_output_value('spider_name') or 'scrapy_crawler'
            self.add_value('update_by', spider_name)
        
        # 如果没有新闻日期，使用当前日期
        if not self.get_output_value('news_date'):
            self.add_value('news_date', datetime.now().strftime('%Y-%m-%d'))
        
        # 如果没有摘要，从内容中提取
        if not self.get_output_value('summary'):
            self.add_summary_from_content()
        
        # 默认不是重点新闻
        if self.get_output_value('is_great') is None:
            self.add_value('is_great', '0')
        
        # 默认是权威来源
        if self.get_output_value('is_authoritative_source') is None:
            self.add_value('is_authoritative_source', True)