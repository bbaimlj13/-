-- =============================================
-- 分布式爬虫系统 数据库初始化脚本
-- 适配提供的Pydantic模型，兼容MySQL 8.0+
-- =============================================

-- 1. 确保数据库存在并设置默认编码
CREATE DATABASE IF NOT EXISTS `tlzn-cns` 
DEFAULT CHARACTER SET utf8mb4 
DEFAULT COLLATE utf8mb4_unicode_ci;

-- 切换到目标数据库
USE `tlzn-cns`;

-- 2. 新闻数据主表（对应 NewsItem 模型）
DROP TABLE IF EXISTS `news`;
CREATE TABLE `news` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '新闻自增ID',
  `title` VARCHAR(500) NOT NULL COMMENT '新闻标题',
  `content` TEXT NOT NULL COMMENT '新闻内容',
  `summary` VARCHAR(1000) NULL DEFAULT NULL COMMENT '新闻摘要',
  `source` VARCHAR(200) NOT NULL COMMENT '新闻来源',
  `original_url` VARCHAR(500) NOT NULL COMMENT '原始URL',
  `news_date` VARCHAR(50) NULL DEFAULT NULL COMMENT '新闻日期（字符串格式，兼容不同格式）',
  `publish_time` DATETIME NULL DEFAULT NULL COMMENT '发布时间（标准化时间）',
  `images` JSON NULL DEFAULT NULL COMMENT '图片URL列表',
  `attachments` JSON NULL DEFAULT NULL COMMENT '附件URL列表',
  `layout` TEXT NULL DEFAULT NULL COMMENT 'HTML布局',
  `category` ENUM('policy', 'weather', 'power') NULL DEFAULT NULL COMMENT '新闻分类（对应NewsCategory枚举）',
  `new_type` INT UNSIGNED NULL DEFAULT NULL COMMENT '新闻类型ID',
  `keywords` JSON NULL DEFAULT NULL COMMENT '关键词列表',
  `author` VARCHAR(100) NULL DEFAULT NULL COMMENT '作者',
  `is_authoritative` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否权威来源（1=是，0=否）',
  `is_top` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否置顶（1=是，0=否）',
  `view_count` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '浏览量',
  `like_count` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '点赞数',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_original_url` (`original_url`) COMMENT 'URL唯一索引，防止重复抓取',
  KEY `idx_source` (`source`) COMMENT '来源索引，便于按来源查询',
  KEY `idx_category` (`category`) COMMENT '分类索引，便于按分类筛选',
  KEY `idx_publish_time` (`publish_time`) COMMENT '发布时间索引，便于按时间排序',
  KEY `idx_created_at` (`created_at`) COMMENT '创建时间索引，便于按入库时间查询'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='新闻数据主表';

-- 3. 爬虫任务表（对应 CrawlerTask 模型）
DROP TABLE IF EXISTS `crawler_tasks`;
CREATE TABLE `crawler_tasks` (
  `task_id` VARCHAR(64) NOT NULL COMMENT '任务ID（UUID或自定义唯一标识）',
  `spider_name` VARCHAR(100) NOT NULL COMMENT '爬虫名称',
  `urls` JSON NOT NULL COMMENT '起始URL列表',
  `config` JSON NULL DEFAULT NULL COMMENT '爬虫配置参数',  -- 修正：移除 DEFAULT '{}'
  `priority` TINYINT UNSIGNED NOT NULL DEFAULT 5 COMMENT '任务优先级（1-10）',
  `max_items` INT UNSIGNED NULL DEFAULT 100 COMMENT '最大抓取数量',
  `status` ENUM('pending', 'running', 'paused', 'completed', 'failed', 'cancelled') NOT NULL DEFAULT 'pending' COMMENT '任务状态（对应TaskStatus枚举）',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '任务创建时间',
  `started_at` DATETIME NULL DEFAULT NULL COMMENT '任务开始时间',
  `completed_at` DATETIME NULL DEFAULT NULL COMMENT '任务完成时间',
  `paused_at` DATETIME NULL DEFAULT NULL COMMENT '任务暂停时间',
  `resumed_at` DATETIME NULL DEFAULT NULL COMMENT '任务恢复时间',
  `cancelled_at` DATETIME NULL DEFAULT NULL COMMENT '任务取消时间',
  `error` TEXT NULL DEFAULT NULL COMMENT '错误信息（任务失败时存储）',
  `total_items` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '总项目数',
  `processed_items` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '已处理项目数',
  `failed_items` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '失败项目数',
  `progress` FLOAT NOT NULL DEFAULT 0.0 COMMENT '任务进度（0-100）',
  `node_id` VARCHAR(64) NULL DEFAULT NULL COMMENT '执行节点ID',
  `metadata` JSON NULL DEFAULT NULL COMMENT '任务元数据',  -- 修正：移除 DEFAULT '{}'
  PRIMARY KEY (`task_id`),
  KEY `idx_spider_name` (`spider_name`) COMMENT '爬虫名称索引，便于按爬虫筛选任务',
  KEY `idx_status` (`status`) COMMENT '状态索引，便于按状态查询任务',
  KEY `idx_node_id` (`node_id`) COMMENT '节点ID索引，便于查询节点执行的任务',
  KEY `idx_created_at` (`created_at`) COMMENT '创建时间索引，便于按时间筛选任务'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='爬虫任务表';

-- 4. 爬虫节点表（对应 CrawlerNode 模型）
DROP TABLE IF EXISTS `crawler_nodes`;
CREATE TABLE `crawler_nodes` (
  `node_id` VARCHAR(64) NOT NULL COMMENT '节点ID（唯一标识）',
  `hostname` VARCHAR(100) NOT NULL COMMENT '节点主机名',
  `ip_address` VARCHAR(50) NOT NULL COMMENT '节点IP地址',
  `status` ENUM('idle', 'running', 'stopped', 'error') NOT NULL DEFAULT 'idle' COMMENT '节点状态（对应SpiderStatus枚举）',
  `active_spiders` JSON NULL DEFAULT NULL COMMENT '活跃爬虫列表',  -- 修正：移除 DEFAULT '[]'
  `cpu_usage` FLOAT NOT NULL DEFAULT 0.0 COMMENT 'CPU使用率（%）',
  `memory_usage` FLOAT NOT NULL DEFAULT 0.0 COMMENT '内存使用率（%）',
  `items_processed` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '节点累计处理项目数',
  `items_failed` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '节点累计失败项目数',
  `last_heartbeat` DATETIME NULL DEFAULT NULL COMMENT '最后心跳时间（用于判断节点是否在线）',
  `started_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '节点启动时间',
  `uptime` FLOAT NOT NULL DEFAULT 0.0 COMMENT '节点运行时间（小时）',
  `version` VARCHAR(50) NOT NULL DEFAULT '1.0.0' COMMENT '节点版本号',
  PRIMARY KEY (`node_id`),
  KEY `idx_status` (`status`) COMMENT '状态索引，便于筛选在线/离线节点',
  KEY `idx_last_heartbeat` (`last_heartbeat`) COMMENT '心跳时间索引，便于清理离线节点'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='爬虫节点表';

-- 5. 爬虫统计表（对应 SpiderStats 模型）
DROP TABLE IF EXISTS `spider_stats`;
CREATE TABLE `spider_stats` (
  `spider_name` VARCHAR(100) NOT NULL COMMENT '爬虫名称（唯一标识）',
  `items_processed` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '累计处理项目数',
  `items_failed` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '累计失败项目数',
  `start_requests` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '累计起始请求数',
  `response_received` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '累计收到响应数',
  `response_failed` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '累计失败响应数',
  `duplicates_filtered` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '累计去重过滤数',
  `last_crawl_time` DATETIME NULL DEFAULT NULL COMMENT '最后爬取时间',
  `avg_response_time` FLOAT NOT NULL DEFAULT 0.0 COMMENT '平均响应时间（秒）',
  `crawl_rate` FLOAT NOT NULL DEFAULT 0.0 COMMENT '爬取速率（个/分钟）',
  `queue_size` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '当前队列大小',
  `dupefilter_size` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '去重集合大小',
  PRIMARY KEY (`spider_name`),
  KEY `idx_last_crawl_time` (`last_crawl_time`) COMMENT '最后爬取时间索引，便于筛选近期活跃爬虫'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='爬虫统计表';

-- 6. 系统日志表（对应 SystemLog 模型）
DROP TABLE IF EXISTS `system_logs`;
CREATE TABLE `system_logs` (
  `id` VARCHAR(64) NOT NULL COMMENT '日志ID（UUID）',
  `timestamp` DATETIME NOT NULL COMMENT '日志产生时间',
  `level` ENUM('debug', 'info', 'warning', 'error', 'critical') NOT NULL COMMENT '日志级别（对应LogLevel枚举）',
  `source` VARCHAR(100) NOT NULL COMMENT '日志来源（如api、crawler-node-1）',
  `message` TEXT NOT NULL COMMENT '日志消息',
  `module` VARCHAR(100) NULL DEFAULT NULL COMMENT '模块名称',
  `function` VARCHAR(100) NULL DEFAULT NULL COMMENT '函数名称',
  `line_number` INT UNSIGNED NULL DEFAULT NULL COMMENT '代码行号',
  `extra_data` JSON NULL DEFAULT NULL COMMENT '额外数据',  -- 修正：移除 DEFAULT '{}'
  PRIMARY KEY (`id`),
  KEY `idx_timestamp` (`timestamp`) COMMENT '时间索引，便于按时间查询日志',
  KEY `idx_level` (`level`) COMMENT '级别索引，便于筛选错误/警告日志',
  KEY `idx_source` (`source`) COMMENT '来源索引，便于按服务筛选日志'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统日志表';

-- 7. 系统警报表（对应 SystemAlert 模型）
DROP TABLE IF EXISTS `system_alerts`;
CREATE TABLE `system_alerts` (
  `id` VARCHAR(64) NOT NULL COMMENT '警报ID（UUID）',
  `timestamp` DATETIME NOT NULL COMMENT '警报产生时间',
  `severity` ENUM('info', 'warning', 'error', 'critical') NOT NULL COMMENT '警报严重程度（对应AlertSeverity枚举）',
  `source` VARCHAR(100) NOT NULL COMMENT '警报来源（如mysql、redis、crawler-node）',
  `message` TEXT NOT NULL COMMENT '警报消息',
  `details` JSON NULL DEFAULT NULL COMMENT '警报详细数据',  -- 修正：移除 DEFAULT '{}'
  `acknowledged` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已确认（1=是，0=否）',
  `acknowledged_by` VARCHAR(100) NULL DEFAULT NULL COMMENT '确认人',
  `acknowledged_at` DATETIME NULL DEFAULT NULL COMMENT '确认时间',
  PRIMARY KEY (`id`),
  KEY `idx_timestamp` (`timestamp`) COMMENT '时间索引，便于按时间查询警报',
  KEY `idx_severity` (`severity`) COMMENT '严重程度索引，便于筛选高危警报',
  KEY `idx_acknowledged` (`acknowledged`) COMMENT '确认状态索引，便于筛选未确认警报'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统警报表';

-- =============================================
-- 初始化完成说明
-- 1. 所有表已设置兼容Pydantic模型的字段和默认值
-- 2. 添加了必要索引提升查询性能
-- 3. 支持JSON类型字段（MySQL 5.7+兼容，8.0+最优）
-- 4. 枚举字段与模型枚举值完全对应
-- 5. 已移除JSON字段的自定义默认值，兼容MySQL 8.0语法
-- =============================================