import os
from typing import Dict, Any

class Config:
    """全局配置类"""
    
    # Redis配置
    REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    
    # MySQL配置
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'mysql')  # 修正：默认值改为容器名
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = os.getenv('MYSQL_USER', 'python')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '123456')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'tlzn-cns')
    
    # MinIO配置
    MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'minio:9000')  # 修正：默认值改为容器名
    MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minio')
    MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'qec429MN')
    MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'tlzn-cns-news')
    MINIO_SECURE = os.getenv('MINIO_SECURE', 'False').lower() == 'true'
    
    # 爬虫配置
    CRAWLER_CONCURRENT_REQUESTS = int(os.getenv('CONCURRENT_REQUESTS', 8))
    CRAWLER_CONCURRENT_REQUESTS_PER_DOMAIN = int(os.getenv('CONCURRENT_REQUESTS_PER_DOMAIN', 2))  # 新增
    CRAWLER_DOWNLOAD_DELAY = float(os.getenv('DOWNLOAD_DELAY', 1.0))
    CRAWLER_AUTOTHROTTLE_ENABLED = os.getenv('AUTOTHROTTLE_ENABLED', 'True').lower() == 'true'  # 新增
    
    # API配置
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', 8000))
    API_DEBUG = os.getenv('API_DEBUG', 'False').lower() == 'true'
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')  
    LOG_FILE = os.getenv('LOG_FILE', 'logs/api_server.log')
    
    @classmethod
    def get_redis_url(cls) -> str:
        if cls.REDIS_PASSWORD:
            return f"redis://:{cls.REDIS_PASSWORD}@{cls.REDIS_HOST}:{cls.REDIS_PORT}/{cls.REDIS_DB}"
        else:
            return f"redis://{cls.REDIS_HOST}:{cls.REDIS_PORT}/{cls.REDIS_DB}"
    
    @classmethod
    def get_mysql_config(cls):
        """兼容性方法：返回MySQL配置字典"""
        return cls.get_mysql_dict()
    
    @classmethod  
    def get_mysql_dict(cls) -> Dict[str, Any]:
        """返回MySQL配置字典"""
        return {
            'host': cls.MYSQL_HOST,
            'port': cls.MYSQL_PORT,
            'user': cls.MYSQL_USER,
            'password': cls.MYSQL_PASSWORD,
            'database': cls.MYSQL_DATABASE,
            'charset': 'utf8mb4'
        }
    
    @classmethod
    def get_minio_config(cls) -> Dict[str, Any]:
        return {
            'endpoint': cls.MINIO_ENDPOINT,
            'access_key': cls.MINIO_ACCESS_KEY,
            'secret_key': cls.MINIO_SECRET_KEY,
            'secure': cls.MINIO_SECURE,
            'bucket_name': cls.MINIO_BUCKET  
        }