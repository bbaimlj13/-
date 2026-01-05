"""
Selenium中间件
用于处理JavaScript渲染的页面
"""

import logging
import scrapy
from scrapy.http import HtmlResponse
from scrapy.utils.python import to_bytes
from scrapy import signals
from scrapy.http import HtmlResponse, TextResponse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import random
import psutil
import signal
import os
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class SeleniumMiddleware:
    """Selenium中间件，用于处理JavaScript渲染的页面"""
    
    def __init__(self):
        self.driver = None
        self.driver_pid = None
        self.use_count = 0
        self.max_use_count = 100  # 每个driver最多使用100次后重启
    
    @classmethod
    def from_crawler(cls, crawler):
        """从爬虫创建中间件实例"""
        middleware = cls()
        crawler.signals.connect(middleware.spider_opened, signal=scrapy.signals.spider_opened)
        crawler.signals.connect(middleware.spider_closed, signal=scrapy.signals.spider_closed)
        return middleware
    
    def spider_opened(self, spider):
        """爬虫打开时初始化Selenium"""
        spider.logger.info(f"初始化Selenium中间件 for {spider.name}")
    
    def spider_closed(self, spider):
        """爬虫关闭时清理Selenium"""
        self.close_driver()
        spider.logger.info(f"关闭Selenium中间件 for {spider.name}")
    
    def process_request(self, request, spider):
        """处理请求"""
        # 检查是否需要使用Selenium
        if not request.meta.get('use_selenium', False):
            return None
        
        spider.logger.debug(f"使用Selenium处理请求: {request.url}")
        
        try:
            # 初始化或获取driver
            driver = self.get_driver(spider)
            if not driver:
                spider.logger.error("无法获取Selenium driver")
                return None
            
            # 访问页面
            spider.logger.info(f"Selenium访问页面: {request.url}")
            driver.get(request.url)
            
            # 随机延迟，模拟人类行为
            delay = random.uniform(2, 4)
            spider.logger.debug(f"Selenium延迟 {delay:.1f} 秒")
            time.sleep(delay)
            
            # 等待页面加载
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # 模拟滚动
                self.simulate_scroll(driver, spider)
                
                # 获取页面源码
                page_source = driver.page_source
                
                # 创建响应对象
                response = HtmlResponse(
                    url=driver.current_url,
                    body=page_source.encode('utf-8'),
                    encoding='utf-8',
                    request=request
                )
                
                # 增加使用计数
                self.use_count += 1
                
                # 如果使用次数过多，重启driver
                if self.use_count >= self.max_use_count:
                    spider.logger.info(f"Selenium driver已达到最大使用次数 {self.max_use_count}，准备重启")
                    self.restart_driver(spider)
                
                return response
                
            except Exception as e:
                spider.logger.warning(f"Selenium等待页面加载失败: {request.url}, 错误: {e}")
                # 即使失败也返回当前页面
                page_source = driver.page_source
                response = HtmlResponse(
                    url=driver.current_url,
                    body=page_source.encode('utf-8'),
                    encoding='utf-8',
                    request=request
                )
                return response
                
        except Exception as e:
            spider.logger.error(f"Selenium处理请求失败: {request.url}, 错误: {e}")
            # 清理driver并重试
            self.restart_driver(spider)
            return None
    
    def get_driver(self, spider):
        """获取或创建WebDriver"""
        if self.driver is None:
            self.driver = self.create_driver(spider)
        return self.driver
    
    def create_driver(self, spider):
        """创建新的WebDriver实例"""
        try:
            # Chrome配置
            chrome_options = Options()
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--lang=zh-CN')
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--ignore-ssl-errors')
            
            # 禁用某些功能以加速
            chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
            chrome_options.add_experimental_option('prefs', {
                'profile.default_content_setting_values.notifications': 2,
                'profile.default_content_setting_values.images': 2,
            })
            
            # 设置ChromeDriver路径
            driver_path = self.get_chromedriver_path()
            if not driver_path:
                spider.logger.error("无法找到ChromeDriver")
                return None
            
            # 创建Service
            service = Service(executable_path=driver_path)
            
            # 创建Driver
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 设置超时
            driver.set_page_load_timeout(30)
            driver.set_script_timeout(30)
            driver.implicitly_wait(10)
            
            # 记录driver的PID
            self.driver_pid = driver.service.process.pid
            
            spider.logger.info("ChromeDriver创建成功")
            return driver
            
        except Exception as e:
            spider.logger.error(f"创建ChromeDriver失败: {e}")
            return None
    
    def get_chromedriver_path(self):
        """获取ChromeDriver路径"""
        import platform
        
        # 可能的路径
        possible_paths = []
        
        # 根据操作系统确定文件名
        system = platform.system().lower()
        if system == "windows":
            driver_name = "chromedriver.exe"
            # Windows系统常见路径
            possible_paths.extend([
                r"C:\xinwen_new\crawler-power_trade-news\drivers\chromedriver.exe",
                r"C:\Program Files\chromedriver\chromedriver.exe",
                r"C:\chromedriver\chromedriver.exe",
                os.path.join(os.getcwd(), "drivers", "chromedriver.exe"),
                os.path.join(os.path.dirname(__file__), "..", "..", "drivers", "chromedriver.exe"),
            ])
        else:  # Linux, Darwin(Mac)
            driver_name = "chromedriver"
            # Unix系统常见路径
            possible_paths.extend([
                "/usr/local/bin/chromedriver",
                "/usr/bin/chromedriver",
                "/opt/chromedriver/chromedriver",
                os.path.join(os.getcwd(), "drivers", "chromedriver"),
                os.path.join(os.path.dirname(__file__), "..", "..", "drivers", "chromedriver"),
                "/usr/local/share/chromedriver-linux64/chromedriver",  # Linux 64位
                "/usr/local/share/chromedriver-mac-arm64/chromedriver",  # Mac ARM
                "/usr/local/share/chromedriver-mac-x64/chromedriver",  # Mac Intel
            ])
        
        # 检查所有可能的路径
        for driver_path in possible_paths:
            if os.path.exists(driver_path):
                logger.info(f"找到ChromeDriver: {driver_path}")
                return driver_path
        
        # 尝试从PATH环境变量中查找
        import shutil
        try:
            driver_path = shutil.which("chromedriver")
            if driver_path:
                logger.info(f"从PATH找到ChromeDriver: {driver_path}")
                return driver_path
        except:
            pass
        
        logger.error(f"未找到ChromeDriver，尝试过的路径: {possible_paths}")
        return None
    
    def simulate_scroll(self, driver, spider):
        """模拟滚动页面"""
        try:
            scroll_count = random.randint(2, 4)
            spider.logger.debug(f"Selenium模拟滚动 {scroll_count} 次")
            
            for i in range(scroll_count):
                scroll_height = random.randint(500, 800)
                driver.execute_script(f"window.scrollBy(0, {scroll_height});")
                time.sleep(random.uniform(1.0, 1.5))
                
        except Exception as e:
            spider.logger.warning(f"Selenium滚动失败: {e}")
    
    def restart_driver(self, spider):
        """重启WebDriver"""
        spider.logger.info("重启Selenium driver")
        self.close_driver()
        self.use_count = 0
        self.driver = self.create_driver(spider)
    
    def close_driver(self):
        """关闭WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("ChromeDriver已关闭")
            except Exception as e:
                logger.warning(f"关闭ChromeDriver时出错: {e}")
            finally:
                self.driver = None
                self.driver_pid = None
        
        # 清理残留的Chrome进程
        self.kill_chrome_processes()
    
    def kill_chrome_processes(self):
        """杀死所有Chrome相关进程"""
        try:
            killed_count = 0
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    proc_name = proc.info['name'].lower() if proc.info.get('name') else ''
                    if proc_name and any(name in proc_name for name in ['chrome', 'chromedriver']):
                        try:
                            os.kill(proc.info['pid'], signal.SIGTERM)
                            logger.debug(f"终止进程: {proc_name} (PID: {proc.info['pid']})")
                            killed_count += 1
                            time.sleep(0.5)
                        except (psutil.NoSuchProcess, ProcessLookupError):
                            pass
                except (psutil.NoSuchProcess, AttributeError):
                    pass
            
            if killed_count > 0:
                logger.info(f"清理了 {killed_count} 个Chrome相关进程")
            
        except Exception as e:
            logger.warning(f"清理Chrome进程时出错: {e}")