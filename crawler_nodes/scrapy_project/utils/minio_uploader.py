"""
MinIO上传工具
封装MinIO上传操作的通用函数
"""

import io
import hashlib
import time
import os
import re
from typing import Optional, Dict, Any
import requests
from minio import Minio
import logging

# 添加项目路径
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from shared.config import Config

logger = logging.getLogger(__name__)

class MinioUploader:
    """MinIO上传工具类"""
    
    def __init__(self):
        self.minio_config = Config.get_minio_config()
        self.bucket_name = self.minio_config['bucket_name']
        self.minio_client = None
        self.uploaded_cache = {}  # URL到MinIO对象名的映射缓存
        
    def initialize(self):
        """初始化MinIO客户端"""
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
            
            logger.info(f"MinIO上传工具初始化成功: {self.minio_config['endpoint']}")
            return True
            
        except Exception as e:
            logger.error(f"MinIO上传工具初始化失败: {e}")
            return False
    
    def upload_image(self, image_url: str, headers: Dict[str, Any] = None) -> Optional[str]:
        """上传图片到MinIO"""
        if not self.minio_client:
            logger.error("MinIO客户端未初始化")
            return None
        
        try:
            # 检查缓存
            if image_url in self.uploaded_cache:
                logger.debug(f"图片已缓存: {image_url}")
                return self.uploaded_cache[image_url]
            
            # 下载图片
            if headers is None:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            
            logger.info(f"下载图片: {image_url}")
            response = requests.get(image_url, headers=headers, timeout=10, stream=True)
            
            if response.status_code != 200:
                logger.warning(f"图片下载失败: {image_url}, 状态码: {response.status_code}")
                return None
            
            # 获取图片数据
            img_data = b''
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    img_data += chunk
            
            if len(img_data) == 0:
                logger.warning(f"图片数据为空: {image_url}")
                return None
            
            # 生成唯一文件名
            ext = self._get_image_extension(response.headers.get('Content-Type', ''), image_url)
            img_md5 = hashlib.md5(img_data).hexdigest()
            timestamp = int(time.time() * 1000)
            obj_name = f"images/{timestamp}_{img_md5}{ext}"
            
            # 检查是否已存在
            try:
                self.minio_client.stat_object(self.bucket_name, obj_name)
                logger.debug(f"图片已存在MinIO: {obj_name}")
                self.uploaded_cache[image_url] = obj_name
                return obj_name
            except:
                pass
            
            # 上传到MinIO
            logger.info(f"上传图片到MinIO: {obj_name}")
            self.minio_client.put_object(
                self.bucket_name,
                obj_name,
                data=io.BytesIO(img_data),
                length=len(img_data),
                content_type=response.headers.get('Content-Type', 'image/jpeg')
            )
            
            # 添加到缓存
            self.uploaded_cache[image_url] = obj_name
            
            logger.info(f"图片上传成功: {obj_name}")
            return obj_name
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"图片下载失败 {image_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"上传图片失败 {image_url}: {e}")
            return None
    
    def upload_attachment(self, attachment_url: str, headers: Dict[str, Any] = None) -> Optional[str]:
        """上传附件到MinIO"""
        if not self.minio_client:
            logger.error("MinIO客户端未初始化")
            return None
        
        try:
            # 下载附件
            if headers is None:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            
            logger.info(f"下载附件: {attachment_url}")
            response = requests.get(attachment_url, headers=headers, timeout=30, stream=True)
            
            if response.status_code != 200:
                logger.warning(f"附件下载失败: {attachment_url}, 状态码: {response.status_code}")
                return None
            
            # 获取文件名
            filename = self._get_filename_from_url(attachment_url, response.headers)
            
            # 检查文件大小（限制为50MB以内）
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > 50 * 1024 * 1024:
                logger.warning(f"附件过大，跳过下载: {attachment_url}, 大小: {content_length}")
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
                        logger.warning(f"附件下载过程中超过大小限制: {attachment_url}")
                        return None
            
            content.seek(0)
            
            # 生成存储名称
            timestamp = int(time.time() * 1000)
            obj_name = f"attachments/{timestamp}_{filename}"
            
            # 检查是否已存在
            try:
                self.minio_client.stat_object(self.bucket_name, obj_name)
                logger.debug(f"附件已存在MinIO: {obj_name}")
                return obj_name
            except:
                pass
            
            # 上传到MinIO
            logger.info(f"上传附件到MinIO: {obj_name}")
            self.minio_client.put_object(
                self.bucket_name,
                obj_name,
                data=content,
                length=total_size,
                content_type=response.headers.get('Content-Type', 'application/octet-stream')
            )
            
            logger.info(f"附件上传成功: {obj_name}, 大小: {total_size}字节")
            return obj_name
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"附件下载失败 {attachment_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"上传附件失败 {attachment_url}: {e}")
            return None
    
    def upload_bytes(self, data: bytes, filename: str, content_type: str = 'application/octet-stream') -> Optional[str]:
        """上传字节数据到MinIO"""
        if not self.minio_client:
            logger.error("MinIO客户端未初始化")
            return None
        
        try:
            # 生成存储名称
            timestamp = int(time.time() * 1000)
            file_md5 = hashlib.md5(data).hexdigest()
            ext = os.path.splitext(filename)[-1] or '.bin'
            obj_name = f"uploads/{timestamp}_{file_md5}{ext}"
            
            # 检查是否已存在
            try:
                self.minio_client.stat_object(self.bucket_name, obj_name)
                logger.debug(f"文件已存在MinIO: {obj_name}")
                return obj_name
            except:
                pass
            
            # 上传到MinIO
            logger.info(f"上传字节数据到MinIO: {obj_name}")
            self.minio_client.put_object(
                self.bucket_name,
                obj_name,
                data=io.BytesIO(data),
                length=len(data),
                content_type=content_type
            )
            
            logger.info(f"字节数据上传成功: {obj_name}, 大小: {len(data)}字节")
            return obj_name
            
        except Exception as e:
            logger.error(f"上传字节数据失败: {e}")
            return None
    
    def _get_image_extension(self, content_type: str, url: str) -> str:
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
        url = url.lower()
        if url.endswith('.jpg') or url.endswith('.jpeg'):
            return '.jpg'
        elif url.endswith('.png'):
            return '.png'
        elif url.endswith('.gif'):
            return '.gif'
        elif url.endswith('.webp'):
            return '.webp'
        elif url.endswith('.bmp'):
            return '.bmp'
        
        # 默认
        return '.jpg'
    
    def _get_filename_from_url(self, url: str, headers: Dict) -> str:
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
    
    def get_object_url(self, obj_name: str, expires: int = 3600) -> Optional[str]:
        """获取对象的临时访问URL"""
        if not self.minio_client:
            logger.error("MinIO客户端未初始化")
            return None
        
        try:
            url = self.minio_client.presigned_get_object(
                self.bucket_name,
                obj_name,
                expires=expires
            )
            return url
        except Exception as e:
            logger.error(f"获取对象URL失败: {e}")
            return None
    
    def cleanup_cache(self):
        """清理缓存"""
        self.uploaded_cache.clear()
        logger.info("MinIO上传缓存已清理")

# 单例实例
_minio_uploader = None

def get_minio_uploader() -> MinioUploader:
    """获取MinIO上传工具实例（单例）"""
    global _minio_uploader
    if _minio_uploader is None:
        _minio_uploader = MinioUploader()
        _minio_uploader.initialize()
    return _minio_uploader