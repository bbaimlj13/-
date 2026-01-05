"""
图片处理工具
处理图片下载、上传、转换等操作
"""

import io
import hashlib
import time
import os
import re
from typing import Optional, Dict, Any, List, Tuple
import requests
from PIL import Image
import logging

# 添加项目路径
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from shared.config import Config

logger = logging.getLogger(__name__)

class ImageHandler:
    """图片处理工具类"""
    
    def __init__(self):
        self.download_timeout = 10
        self.max_image_size = 10 * 1024 * 1024  # 10MB
        self.supported_formats = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']
        self.cache_dir = "cache/images"
        
        # 创建缓存目录
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def download_image(self, url: str, headers: Dict[str, Any] = None) -> Optional[bytes]:
        """下载图片"""
        try:
            if headers is None:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            
            logger.info(f"下载图片: {url}")
            response = requests.get(url, headers=headers, timeout=self.download_timeout, stream=True)
            
            if response.status_code != 200:
                logger.warning(f"图片下载失败: {url}, 状态码: {response.status_code}")
                return None
            
            # 检查内容类型
            content_type = response.headers.get('Content-Type', '').lower()
            if not any(fmt in content_type for fmt in ['image', 'octet-stream']):
                logger.warning(f"非图片内容类型: {url}, Content-Type: {content_type}")
                return None
            
            # 获取图片数据
            img_data = b''
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    img_data += chunk
                    
                    # 检查大小限制
                    if len(img_data) > self.max_image_size:
                        logger.warning(f"图片过大，停止下载: {url}, 大小: {len(img_data)}")
                        return None
            
            if len(img_data) == 0:
                logger.warning(f"图片数据为空: {url}")
                return None
            
            logger.info(f"图片下载成功: {url}, 大小: {len(img_data)}字节")
            return img_data
            
        except requests.exceptions.Timeout:
            logger.warning(f"图片下载超时: {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"图片下载失败 {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"下载图片时发生错误 {url}: {e}")
            return None
    
    def process_image(self, img_data: bytes, max_width: int = 1920, max_height: int = 1080, 
                      quality: int = 85) -> Optional[bytes]:
        """处理图片（调整大小、压缩等）"""
        try:
            # 打开图片
            img = Image.open(io.BytesIO(img_data))
            original_format = img.format
            
            # 检查格式是否支持
            if original_format and original_format.lower() not in self.supported_formats:
                logger.warning(f"不支持的图片格式: {original_format}")
                return None
            
            # 转换为RGB模式（如果必要）
            if img.mode in ('RGBA', 'LA', 'P'):
                # 创建白色背景
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    # 合并RGBA图片到白色背景
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img, mask=None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 调整大小（如果需要）
            img_width, img_height = img.size
            if img_width > max_width or img_height > max_height:
                # 计算新的尺寸
                ratio = min(max_width / img_width, max_height / img_height)
                new_width = int(img_width * ratio)
                new_height = int(img_height * ratio)
                
                logger.debug(f"调整图片尺寸: {img_width}x{img_height} -> {new_width}x{new_height}")
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 保存为JPEG格式
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            processed_data = output.getvalue()
            
            logger.info(f"图片处理完成: 原始大小 {len(img_data)}字节 -> 处理后 {len(processed_data)}字节")
            return processed_data
            
        except Exception as e:
            logger.error(f"处理图片失败: {e}")
            return None
    
    def get_image_info(self, img_data: bytes) -> Optional[Dict[str, Any]]:
        """获取图片信息"""
        try:
            img = Image.open(io.BytesIO(img_data))
            
            info = {
                'format': img.format,
                'mode': img.mode,
                'size': img.size,
                'width': img.width,
                'height': img.height,
                'file_size': len(img_data)
            }
            
            return info
            
        except Exception as e:
            logger.error(f"获取图片信息失败: {e}")
            return None
    
    def save_to_cache(self, url: str, img_data: bytes) -> Optional[str]:
        """保存图片到缓存"""
        try:
            # 生成缓存文件名
            url_md5 = hashlib.md5(url.encode()).hexdigest()
            ext = self._guess_extension(img_data)
            cache_filename = f"{url_md5}{ext}"
            cache_path = os.path.join(self.cache_dir, cache_filename)
            
            # 保存到文件
            with open(cache_path, 'wb') as f:
                f.write(img_data)
            
            logger.debug(f"图片已保存到缓存: {cache_path}")
            return cache_path
            
        except Exception as e:
            logger.error(f"保存图片到缓存失败: {e}")
            return None
    
    def load_from_cache(self, url: str) -> Optional[bytes]:
        """从缓存加载图片"""
        try:
            # 生成缓存文件名
            url_md5 = hashlib.md5(url.encode()).hexdigest()
            
            # 查找缓存文件
            for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
                cache_path = os.path.join(self.cache_dir, f"{url_md5}{ext}")
                if os.path.exists(cache_path):
                    with open(cache_path, 'rb') as f:
                        img_data = f.read()
                    
                    logger.debug(f"从缓存加载图片: {cache_path}")
                    return img_data
            
            return None
            
        except Exception as e:
            logger.error(f"从缓存加载图片失败: {e}")
            return None
    
    def generate_filename(self, url: str, img_data: bytes, prefix: str = "image") -> str:
        """生成文件名"""
        try:
            # 计算MD5
            img_md5 = hashlib.md5(img_data).hexdigest()
            
            # 获取扩展名
            ext = self._guess_extension(img_data)
            
            # 从URL提取原始文件名（如果有）
            url_filename = self._extract_filename_from_url(url)
            if url_filename and len(url_filename) < 50:
                # 清理文件名
                clean_name = re.sub(r'[^\w\u4e00-\u9fff\-\.]', '_', url_filename)
                filename = f"{prefix}_{img_md5[:8]}_{clean_name}"
            else:
                filename = f"{prefix}_{img_md5}"
            
            # 确保文件名长度合理
            if len(filename) > 150:
                filename = filename[:150]
            
            return f"{filename}{ext}"
            
        except Exception as e:
            logger.error(f"生成文件名失败: {e}")
            timestamp = int(time.time() * 1000)
            return f"{prefix}_{timestamp}.jpg"
    
    def batch_process_images(self, urls: List[str], headers: Dict[str, Any] = None) -> List[Tuple[str, Optional[bytes]]]:
        """批量处理图片"""
        results = []
        
        for url in urls:
            try:
                # 首先检查缓存
                cached_data = self.load_from_cache(url)
                if cached_data:
                    results.append((url, cached_data))
                    continue
                
                # 下载图片
                img_data = self.download_image(url, headers)
                if not img_data:
                    results.append((url, None))
                    continue
                
                # 处理图片
                processed_data = self.process_image(img_data)
                if not processed_data:
                    results.append((url, None))
                    continue
                
                # 保存到缓存
                self.save_to_cache(url, processed_data)
                
                results.append((url, processed_data))
                
            except Exception as e:
                logger.error(f"批量处理图片失败 {url}: {e}")
                results.append((url, None))
        
        return results
    
    def cleanup_cache(self, max_age_hours: int = 24):
        """清理缓存"""
        try:
            current_time = time.time()
            deleted_count = 0
            
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                
                # 获取文件修改时间
                file_mtime = os.path.getmtime(filepath)
                file_age_hours = (current_time - file_mtime) / 3600
                
                # 如果文件超过指定时间，删除
                if file_age_hours > max_age_hours:
                    os.remove(filepath)
                    deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"清理缓存: 删除 {deleted_count} 个旧文件")
                
        except Exception as e:
            logger.error(f"清理缓存失败: {e}")
    
    def _guess_extension(self, img_data: bytes) -> str:
        """猜测图片扩展名"""
        try:
            # 检查文件头
            if img_data.startswith(b'\xff\xd8\xff'):
                return '.jpg'
            elif img_data.startswith(b'\x89PNG\r\n\x1a\n'):
                return '.png'
            elif img_data.startswith(b'GIF87a') or img_data.startswith(b'GIF89a'):
                return '.gif'
            elif img_data.startswith(b'RIFF') and img_data[8:12] == b'WEBP':
                return '.webp'
            elif img_data.startswith(b'BM'):
                return '.bmp'
            else:
                # 尝试用PIL打开
                img = Image.open(io.BytesIO(img_data))
                if img.format:
                    return f".{img.format.lower()}"
        except:
            pass
        
        return '.jpg'
    
    def _extract_filename_from_url(self, url: str) -> Optional[str]:
        """从URL中提取文件名"""
        try:
            # 移除查询参数
            url = url.split('?')[0]
            
            # 获取最后一部分
            filename = os.path.basename(url)
            
            # 检查是否是有效的文件名
            if filename and '.' in filename and len(filename) > 3:
                return filename
            
            return None
            
        except Exception:
            return None

# 单例实例
_image_handler = None

def get_image_handler() -> ImageHandler:
    """获取图片处理工具实例（单例）"""
    global _image_handler
    if _image_handler is None:
        _image_handler = ImageHandler()
    return _image_handler