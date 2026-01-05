"""
MySQL数据库写入工具
封装MySQL数据库操作的通用函数
"""

import json
import logging
import pymysql
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager

# 添加项目路径
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from shared.config import Config

logger = logging.getLogger(__name__)

class MySQLWriter:
    """MySQL数据库写入工具类"""
    
    def __init__(self):
        self.db_config = Config.get_mysql_config()
        self.connection_pool = None
        
    def initialize(self):
        """初始化数据库连接池"""
        try:
            # 这里可以添加连接池实现
            # 目前使用简单的连接管理
            logger.info(f"MySQL写入工具初始化成功: {self.db_config['host']}:{self.db_config['port']}")
            return True
        except Exception as e:
            logger.error(f"MySQL写入工具初始化失败: {e}")
            return False
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        connection = None
        cursor = None
        
        try:
            connection = pymysql.connect(**self.db_config)
            cursor = connection.cursor()
            yield connection, cursor
        except Exception as e:
            logger.error(f"获取数据库连接失败: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
    
    def save_news_item(self, item: Dict[str, Any]) -> bool:
        """保存新闻项目到数据库"""
        try:
            with self.get_connection() as (conn, cursor):
                # 检查是否已存在
                if self._is_duplicate(item, cursor):
                    logger.info(f"新闻已存在，跳过: {item.get('title', 'Unknown')[:50]}...")
                    return False
                
                # 插入数据
                self._insert_item(item, conn, cursor)
                logger.info(f"新闻已保存到数据库: {item.get('title', 'Unknown')[:50]}...")
                return True
                
        except Exception as e:
            logger.error(f"保存新闻项目失败: {e}")
            return False
    
    def batch_save_news_items(self, items: List[Dict[str, Any]]) -> Tuple[int, int]:
        """批量保存新闻项目到数据库"""
        success_count = 0
        fail_count = 0
        
        try:
            with self.get_connection() as (conn, cursor):
                for item in items:
                    try:
                        # 检查是否已存在
                        if self._is_duplicate(item, cursor):
                            logger.debug(f"新闻已存在，跳过: {item.get('title', 'Unknown')[:50]}...")
                            continue
                        
                        # 插入数据
                        self._insert_item(item, conn, cursor)
                        success_count += 1
                        
                        # 每插入10条提交一次
                        if success_count % 10 == 0:
                            conn.commit()
                            logger.debug(f"批量插入已提交 {success_count} 条记录")
                            
                    except Exception as e:
                        fail_count += 1
                        logger.error(f"批量插入项目失败: {e}")
                
                # 提交剩余的更改
                conn.commit()
                
                logger.info(f"批量保存完成: 成功 {success_count}, 失败 {fail_count}")
                return success_count, fail_count
                
        except Exception as e:
            logger.error(f"批量保存新闻项目失败: {e}")
            return success_count, fail_count + len(items) - success_count
    
    def _is_duplicate(self, item: Dict[str, Any], cursor) -> bool:
        """检查是否重复"""
        try:
            # 使用URL作为唯一标识
            check_sql = """
                SELECT 1 FROM cns_news_data 
                WHERE original_url = %s OR (title = %s AND news_date = %s AND source = %s)
                LIMIT 1
            """
            
            cursor.execute(check_sql, (
                item.get('original_url'),
                item.get('title', '')[:200],
                item.get('news_date'),
                item.get('source', '')[:50]
            ))
            
            return cursor.fetchone() is not None
            
        except Exception as e:
            logger.error(f"检查重复失败: {e}")
            return False
    
    def _insert_item(self, item: Dict[str, Any], conn, cursor):
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
            cursor.execute(insert_sql, (
                title, content, summary, original_url, attachments,
                source, new_type, news_date, images, update_by,
                layout, create_time, create_by, update_time, is_great,
                is_authoritative_source, topic_ids
            ))
            
        except Exception as e:
            conn.rollback()
            raise
    
    def get_news_count(self, spider_name: str = None) -> int:
        """获取新闻数量"""
        try:
            with self.get_connection() as (conn, cursor):
                if spider_name:
                    sql = "SELECT COUNT(*) FROM cns_news_data WHERE create_by = %s"
                    cursor.execute(sql, (spider_name,))
                else:
                    sql = "SELECT COUNT(*) FROM cns_news_data"
                    cursor.execute(sql)
                
                result = cursor.fetchone()
                return result[0] if result else 0
                
        except Exception as e:
            logger.error(f"获取新闻数量失败: {e}")
            return 0
    
    def get_recent_news(self, limit: int = 10, spider_name: str = None) -> List[Dict[str, Any]]:
        """获取最近的新闻"""
        try:
            with self.get_connection() as (conn, cursor):
                if spider_name:
                    sql = """
                        SELECT id, title, source, news_date, create_time 
                        FROM cns_news_data 
                        WHERE create_by = %s
                        ORDER BY create_time DESC 
                        LIMIT %s
                    """
                    cursor.execute(sql, (spider_name, limit))
                else:
                    sql = """
                        SELECT id, title, source, news_date, create_time 
                        FROM cns_news_data 
                        ORDER BY create_time DESC 
                        LIMIT %s
                    """
                    cursor.execute(sql, (limit,))
                
                columns = [desc[0] for desc in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    result = dict(zip(columns, row))
                    results.append(result)
                
                return results
                
        except Exception as e:
            logger.error(f"获取最近新闻失败: {e}")
            return []
    
    def delete_old_news(self, days: int = 30) -> int:
        """删除旧新闻"""
        try:
            with self.get_connection() as (conn, cursor):
                sql = """
                    DELETE FROM cns_news_data 
                    WHERE create_time < DATE_SUB(NOW(), INTERVAL %s DAY)
                """
                cursor.execute(sql, (days,))
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"删除 {deleted_count} 条 {days} 天前的旧新闻")
                return deleted_count
                
        except Exception as e:
            logger.error(f"删除旧新闻失败: {e}")
            return 0
    
    def update_news_statistics(self, spider_name: str, item_count: int, success: bool = True):
        """更新新闻统计信息"""
        try:
            with self.get_connection() as (conn, cursor):
                # 这里可以创建统计表或更新统计信息
                # 示例：更新爬虫统计
                pass
                
        except Exception as e:
            logger.error(f"更新新闻统计失败: {e}")

# 单例实例
_mysql_writer = None

def get_mysql_writer() -> MySQLWriter:
    """获取MySQL写入工具实例（单例）"""
    global _mysql_writer
    if _mysql_writer is None:
        _mysql_writer = MySQLWriter()
        _mysql_writer.initialize()
    return _mysql_writer
