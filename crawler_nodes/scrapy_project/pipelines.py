"""
Scrapy管道定义
处理爬取的数据，包括数据库存储、图片上传等
"""

import logging
import json
import pymysql
from minio import Minio
import hashlib
import io
import time
from datetime import datetime
from scrapy.utils.project import get_project_settings
from urllib.parse import urljoin
import requests
from typing import Dict, List, Any, Optional
import re
import scrapy
# 添加项目路径
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from shared.config import Config
from shared.models import NewsItem as PydanticNewsItem
from shared.constants import NEWS_TYPE_ID_MAP

logger = logging.getLogger(__name__)

class NewsValidationPipeline:
    """新闻数据验证管道"""
    
    def process_item(self, item, spider):
        """验证新闻数据"""
        try:
            # 检查必要字段
            required_fields = ['title', 'content', 'original_url', 'source']
            for field in required_fields:
                if not item.get(field):
                    spider.logger.warning(f"缺少必要字段 {field}: {item.get('title', 'Unknown')}")
                    raise scrapy.exceptions.DropItem(f"缺少必要字段 {field}")
            
            # 验证内容长度
            if len(item.get('content', '').strip()) < 50:
                spider.logger.warning(f"内容过短: {item.get('title', 'Unknown')}")
                raise scrapy.exceptions.DropItem("内容过短")
            
            # 验证标题长度
            if len(item.get('title', '').strip()) < 5:
                spider.logger.warning(f"标题过短: {item.get('title', 'Unknown')}")
                raise scrapy.exceptions.DropItem("标题过短")
            
            # 清理和标准化字段
            self.clean_and_normalize(item)
            
            return item
            
        except Exception as e:
            spider.logger.error(f"数据验证失败: {e}")
            raise scrapy.exceptions.DropItem(f"数据验证失败: {e}")
    
    def clean_and_normalize(self, item):
        """清理和标准化数据"""
        # 确保images是列表
        if 'images' in item and not isinstance(item['images'], list):
            item['images'] = []
        
        # 确保attachments是列表
        if 'attachments' in item and not isinstance(item['attachments'], list):
            item['attachments'] = []
        
        # 确保topic_ids是列表
        if 'topic_ids' in item and not isinstance(item['topic_ids'], list):
            item['topic_ids'] = []
        
        # 清理标题
        if 'title' in item:
            # 移除多余空白
            item['title'] = re.sub(r'\s+', ' ', item['title']).strip()
            # 限制长度
            if len(item['title']) > 500:
                item['title'] = item['title'][:497] + '...'
        
        # 清理内容
        if 'content' in item:
            # 移除多余空白
            item['content'] = re.sub(r'\s+', ' ', item['content']).strip()
            # 限制长度
            if len(item['content']) > 10000:
                item['content'] = item['content'][:9997] + '...'

class DatabasePipeline:
    """MySQL数据库存储管道"""
    
    def __init__(self):
        self.db_config = Config.get_mysql_config()
        self.connection = None
        self.cursor = None
    
    @classmethod
    def from_crawler(cls, crawler):
        """从爬虫创建管道实例"""
        pipeline = cls()
        crawler.signals.connect(pipeline.spider_opened, signal=scrapy.signals.spider_opened)
        crawler.signals.connect(pipeline.spider_closed, signal=scrapy.signals.spider_closed)
        return pipeline
    
    def spider_opened(self, spider):
        """爬虫打开时连接数据库"""
        try:
            self.connection = pymysql.connect(**self.db_config)
            self.cursor = self.connection.cursor()
            spider.logger.info(f"数据库连接成功: {self.db_config['host']}:{self.db_config['port']}")
        except Exception as e:
            spider.logger.error(f"数据库连接失败: {e}")
            raise
    
    def spider_closed(self, spider):
        """爬虫关闭时关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        spider.logger.info("数据库连接已关闭")
    
    def process_item(self, item, spider):
        """处理并保存新闻数据到数据库"""
        try:
            # 检查是否已存在
            if not self.is_duplicate(item, spider):
                # 插入数据
                self.insert_item(item, spider)
                spider.logger.info(f"新闻已保存到数据库: {item.get('title', 'Unknown')[:50]}...")
            else:
                spider.logger.info(f"新闻已存在，跳过: {item.get('title', 'Unknown')[:50]}...")
            
            return item
            
        except pymysql.Error as e:
            spider.logger.error(f"数据库操作失败: {e}")
            self.connection.rollback()
            raise scrapy.exceptions.DropItem(f"数据库操作失败: {e}")
        except Exception as e:
            spider.logger.error(f"保存新闻到数据库失败: {e}")
            raise scrapy.exceptions.DropItem(f"保存新闻到数据库失败: {e}")
    
    def is_duplicate(self, item, spider) -> bool:
        """检查是否重复"""
        try:
            # 使用URL作为唯一标识
            check_sql = """
                SELECT 1 FROM cns_news_data 
                WHERE original_url = %s OR (title = %s AND news_date = %s)
                LIMIT 1
            """
            
            self.cursor.execute(check_sql, (
                item.get('original_url'),
                item.get('title', '')[:200],
                item.get('news_date')
            ))
            
            return self.cursor.fetchone() is not None
            
        except Exception as e:
            spider.logger.error(f"检查重复失败: {e}")
            return False
    
    def insert_item(self, item, spider):
        """插入新闻数据"""
        try:
            # 构建插入SQL
            insert_sql = """
                INSERT INTO cns_news_data (
                    title, content, summary, original_url, attachments, 
                    source, new_type, news_date, images, update_by, 
                    layout, create_time, create_by, update_time, is_great,
                    is_authoritative_source, topic_ids
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # 准备数据
            title = item.get('title', '')[:500]
            content = item.get('content', '')[:10000]
            summary = item.get('summary', '')[:1000] if item.get('summary') else None
            original_url = item.get('original_url', '')[:1000]
            attachments = json.dumps(item.get('attachments', []), ensure_ascii=False)
            source = item.get('source', '')[:100]
            new_type = item.get('new_type')
            news_date = item.get('news_date')
            images = json.dumps(item.get('images', []), ensure_ascii=False)
            update_by = item.get('update_by', 'scrapy_crawler')
            layout = item.get('layout', '')[:15000] if item.get('layout') else ''
            create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            create_by = item.get('create_by', 'scrapy_crawler')
            update_time = None
            is_great = 1 if item.get('is_great') == '1' or item.get('is_great') is True else 0
            is_authoritative_source = 1 if item.get('is_authoritative_source') else 0
            topic_ids = json.dumps(item.get('topic_ids', []), ensure_ascii=False)
            
            # 执行插入
            self.cursor.execute(insert_sql, (
                title, content, summary, original_url, attachments,
                source, new_type, news_date, images, update_by,
                layout, create_time, create_by, update_time, is_great,
                is_authoritative_source, topic_ids
            ))
            
            self.connection.commit()
            
            # 更新统计
            self.update_statistics(spider)
            
        except Exception as e:
            self.connection.rollback()
            raise
    
    def update_statistics(self, spider):
        """更新统计信息"""
        try:
            # 这里可以添加统计更新逻辑
            # 例如：记录爬虫抓取数量、成功率等
            pass
        except Exception as e:
            spider.logger.error(f"更新统计失败: {e}")

class ImageUploadPipeline:
    """图片上传到MinIO的管道"""
    
    def __init__(self):
        self.minio_config = Config.get_minio_config()
        self.bucket_name = self.minio_config.get('bucket_name', Config.MINIO_BUCKET)
        self.minio_client = None
        self.uploaded_cache = {}  # 缓存已上传的图片
    
    @classmethod
    def from_crawler(cls, crawler):
        """从爬虫创建管道实例"""
        pipeline = cls()
        crawler.signals.connect(pipeline.spider_opened, signal=scrapy.signals.spider_opened)
        return pipeline
    
    def spider_opened(self, spider):
        """爬虫打开时初始化MinIO客户端"""
        try:
            self.minio_client = Minio(
                self.minio_config['endpoint'],
                access_key=self.minio_config['access_key'],
                secret_key=self.minio_config['secret_key'],
                secure=self.minio_config['secure']
            )
            
            # 确保桶存在
            if not self.minio_client.bucket_exists(self.bucket_name):
                self.minio_client.make_bucket(self.bucket_name)
            
            spider.logger.info(f"MinIO连接成功: {self.minio_config['endpoint']}")
            
        except Exception as e:
            spider.logger.error(f"MinIO连接失败: {e}")
            self.minio_client = None
    
    def process_item(self, item, spider):
        """处理图片上传"""
        if not self.minio_client:
            spider.logger.warning("MinIO客户端未初始化，跳过图片上传")
            return item
        
        try:
            images = item.get('images', [])
            uploaded_images = []
            
            for img_url in images:
                try:
                    # 上传图片到MinIO
                    obj_name = self.upload_image(img_url, spider)
                    if obj_name:
                        uploaded_images.append(obj_name)
                except Exception as e:
                    spider.logger.warning(f"图片上传失败 {img_url}: {e}")
            
            # 如果没有图片，使用默认图片
            if not uploaded_images:
                default_image = self.get_default_image(item.get('new_type'), spider)
                if default_image:
                    uploaded_images.append(default_image)
            
            # 更新item中的图片
            item['images'] = uploaded_images
            
            return item
            
        except Exception as e:
            spider.logger.error(f"处理图片上传失败: {e}")
            return item
    
    def upload_image(self, img_url: str, spider) -> Optional[str]:
        """上传单张图片"""
        try:
            # 检查缓存
            if img_url in self.uploaded_cache:
                spider.logger.debug(f"图片已缓存: {img_url}")
                return self.uploaded_cache[img_url]
            
            # 下载图片
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            spider.logger.info(f"下载图片: {img_url}")
            response = requests.get(img_url, headers=headers, timeout=10, stream=True)
            
            if response.status_code != 200:
                spider.logger.warning(f"图片下载失败: {img_url}, 状态码: {response.status_code}")
                return None
            
            # 获取图片数据
            img_data = b''
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    img_data += chunk
            
            if len(img_data) == 0:
                spider.logger.warning(f"图片数据为空: {img_url}")
                return None
            
            # 生成唯一文件名
            ext = self.get_image_extension(response.headers.get('Content-Type', ''), img_url)
            img_md5 = hashlib.md5(img_data).hexdigest()
            timestamp = int(time.time() * 1000)
            obj_name = f"images/{timestamp}_{img_md5}{ext}"
            
            # 检查是否已存在
            try:
                self.minio_client.stat_object(self.bucket_name, obj_name)
                spider.logger.debug(f"图片已存在MinIO: {obj_name}")
                self.uploaded_cache[img_url] = obj_name
                return obj_name
            except:
                pass
            
            # 上传到MinIO
            spider.logger.info(f"上传图片到MinIO: {obj_name}")
            self.minio_client.put_object(
                self.bucket_name,
                obj_name,
                data=io.BytesIO(img_data),
                length=len(img_data),
                content_type=response.headers.get('Content-Type', 'image/jpeg')
            )
            
            # 添加到缓存
            self.uploaded_cache[img_url] = obj_name
            
            spider.logger.info(f"图片上传成功: {obj_name}")
            return obj_name
            
        except requests.exceptions.RequestException as e:
            spider.logger.warning(f"图片下载失败 {img_url}: {e}")
            return None
        except Exception as e:
            spider.logger.error(f"上传图片失败 {img_url}: {e}")
            return None
    
    def get_image_extension(self, content_type: str, img_url: str) -> str:
        """获取图片扩展名"""
        # 根据Content-Type判断
        content_type = content_type.lower()
        if 'jpeg' in content_type or 'jpg' in content_type:
            return '.jpg'
        elif 'png' in content_type:
            return '.png'
        elif 'gif' in content_type:
            return '.gif'
        elif 'webp' in content_type:
            return '.webp'
        
        # 根据URL判断
        img_url = img_url.lower()
        if img_url.endswith('.jpg') or img_url.endswith('.jpeg'):
            return '.jpg'
        elif img_url.endswith('.png'):
            return '.png'
        elif img_url.endswith('.gif'):
            return '.gif'
        elif img_url.endswith('.webp'):
            return '.webp'
        elif img_url.endswith('.bmp'):
            return '.bmp'
        
        # 默认
        return '.jpg'
    
    def get_default_image(self, new_type: int, spider) -> Optional[str]:
        """获取默认图片"""
        try:
            # 根据新闻类型选择默认图片
            category_dirs = {
                41: 'policy',   # 政策类
                42: 'weather',  # 天气类
                43: 'power'     # 电力行业类
            }
            
            category = category_dirs.get(new_type, 'policy')
            default_image = f"default_{category}.jpg"
            
            # 这里可以返回一个预定义的默认图片名称
            # 实际应用中，这些图片应该预先上传到MinIO
            return f"default/{default_image}"
            
        except Exception as e:
            spider.logger.error(f"获取默认图片失败: {e}")
            return None

class AttachmentUploadPipeline:
    """附件上传到MinIO的管道"""
    
    def __init__(self):
        self.minio_config = Config.get_minio_config()
        self.bucket_name = self.minio_config.get('bucket_name', Config.MINIO_BUCKET)
        self.minio_client = None
    
    @classmethod
    def from_crawler(cls, crawler):
        """从爬虫创建管道实例"""
        pipeline = cls()
        crawler.signals.connect(pipeline.spider_opened, signal=scrapy.signals.spider_opened)
        return pipeline
    
    def spider_opened(self, spider):
        """爬虫打开时初始化MinIO客户端"""
        try:
            self.minio_client = Minio(
                self.minio_config['endpoint'],
                access_key=self.minio_config['access_key'],
                secret_key=self.minio_config['secret_key'],
                secure=self.minio_config['secure']
            )
            spider.logger.info(f"MinIO连接成功: {self.minio_config['endpoint']}")
        except Exception as e:
            spider.logger.error(f"MinIO连接失败: {e}")
            self.minio_client = None
    
    def process_item(self, item, spider):
        """处理附件上传"""
        if not self.minio_client:
            spider.logger.warning("MinIO客户端未初始化，跳过附件上传")
            return item
        
        try:
            attachments = item.get('attachments', [])
            uploaded_attachments = []
            
            for att_url in attachments:
                try:
                    # 上传附件到MinIO
                    obj_name = self.upload_attachment(att_url, spider)
                    if obj_name:
                        uploaded_attachments.append(obj_name)
                except Exception as e:
                    spider.logger.warning(f"附件上传失败 {att_url}: {e}")
            
            # 更新item中的附件
            item['attachments'] = uploaded_attachments
            
            return item
            
        except Exception as e:
            spider.logger.error(f"处理附件上传失败: {e}")
            return item
    
    def upload_attachment(self, attachment_url: str, spider) -> Optional[str]:
        """上传单个附件"""
        try:
            # 下载附件
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            spider.logger.info(f"下载附件: {attachment_url}")
            response = requests.get(attachment_url, headers=headers, timeout=30, stream=True)
            
            if response.status_code != 200:
                spider.logger.warning(f"附件下载失败: {attachment_url}, 状态码: {response.status_code}")
                return None
            
            # 获取文件名
            filename = self.get_filename_from_url(attachment_url, response.headers)
            
            # 检查文件大小（限制为50MB以内）
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > 50 * 1024 * 1024:
                spider.logger.warning(f"附件过大，跳过下载: {attachment_url}, 大小: {content_length}")
                return None
            
            # 读取内容
            content = io.BytesIO()
            total_size = 0
            
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    content.write(chunk)
                    total_size += len(chunk)
                    # 如果超过50MB，停止下载
                    if total_size > 50 * 1024 * 1024:
                        spider.logger.warning(f"附件下载过程中超过大小限制: {attachment_url}")
                        return None
            
            content.seek(0)
            
            # 生成存储名称
            timestamp = int(time.time() * 1000)
            obj_name = f"attachments/{timestamp}_{filename}"
            
            # 检查是否已存在
            try:
                self.minio_client.stat_object(self.bucket_name, obj_name)
                spider.logger.debug(f"附件已存在MinIO: {obj_name}")
                return obj_name
            except:
                pass
            
            # 上传到MinIO
            spider.logger.info(f"上传附件到MinIO: {obj_name}")
            self.minio_client.put_object(
                self.bucket_name,
                obj_name,
                data=content,
                length=total_size,
                content_type=response.headers.get('Content-Type', 'application/octet-stream')
            )
            
            spider.logger.info(f"附件上传成功: {obj_name}, 大小: {total_size}字节")
            return obj_name
            
        except requests.exceptions.RequestException as e:
            spider.logger.warning(f"附件下载失败 {attachment_url}: {e}")
            return None
        except Exception as e:
            spider.logger.error(f"上传附件失败 {attachment_url}: {e}")
            return None
    
    def get_filename_from_url(self, url: str, headers: Dict) -> str:
        """从URL和响应头中获取文件名"""
        # 尝试从Content-Disposition获取文件名
        content_disposition = headers.get('Content-Disposition', '')
        if 'filename=' in content_disposition:
            match = re.search(r'filename="?([^"]+)"?', content_disposition)
            if match:
                filename = match.group(1)
                # 清理文件名
                filename = re.sub(r'[^\w\u4e00-\u9fff\-\.]', '_', filename)
                if len(filename) > 100:
                    filename = filename[:100]
                return filename
        
        # 从URL中提取文件名
        parsed_url = url.split('?')[0]  # 去掉查询参数
        filename = os.path.basename(parsed_url)
        
        if not filename or len(filename) < 3:
            filename = f"attachment_{int(time.time())}"
        
        # 清理文件名
        filename = re.sub(r'[^\w\u4e00-\u9fff\-\.]', '_', filename)
        if len(filename) > 100:
            filename = filename[:100]
        
        return filename

class StatisticsPipeline:
    """统计信息管道"""
    
    def __init__(self):
        self.item_count = 0
        self.error_count = 0
        self.start_time = time.time()
    
    @classmethod
    def from_crawler(cls, crawler):
        """从爬虫创建管道实例"""
        pipeline = cls()
        crawler.signals.connect(pipeline.spider_closed, signal=scrapy.signals.spider_closed)
        return pipeline
    
    def process_item(self, item, spider):
        """处理项目，更新统计"""
        self.item_count += 1
        
        # 每处理10个项目记录一次
        if self.item_count % 10 == 0:
            elapsed_time = time.time() - self.start_time
            items_per_minute = (self.item_count / elapsed_time) * 60 if elapsed_time > 0 else 0
            
            spider.logger.info(
                f"统计: 已处理 {self.item_count} 个项目, "
                f"错误: {self.error_count}, "
                f"速率: {items_per_minute:.2f} 项目/分钟"
            )
        
        return item
    
    def spider_closed(self, spider, reason):
        """爬虫关闭时输出最终统计"""
        elapsed_time = time.time() - self.start_time
        items_per_minute = (self.item_count / elapsed_time) * 60 if elapsed_time > 0 else 0
        
        spider.logger.info("=" * 60)
        spider.logger.info("爬虫统计信息:")
        spider.logger.info(f"  运行时间: {elapsed_time:.2f} 秒")
        spider.logger.info(f"  处理项目: {self.item_count}")
        spider.logger.info(f"  错误数量: {self.error_count}")
        spider.logger.info(f"  处理速率: {items_per_minute:.2f} 项目/分钟")
        spider.logger.info(f"  关闭原因: {reason}")
        spider.logger.info("=" * 60)

class RedisPipeline:
    """Redis管道，用于缓存和去重"""
    
    def __init__(self):
        self.redis_url = Config.get_redis_url()
    
    @classmethod
    def from_crawler(cls, crawler):
        """从爬虫创建管道实例"""
        pipeline = cls()
        crawler.signals.connect(pipeline.spider_opened, signal=scrapy.signals.spider_opened)
        return pipeline
    
    def spider_opened(self, spider):
        """爬虫打开时初始化"""
        # Scrapy-Redis会自动处理
        spider.logger.info(f"使用Redis进行去重和队列管理: {self.redis_url}")
    
    def process_item(self, item, spider):
        """处理项目"""
        # 这里可以添加自定义的Redis逻辑
        return item