#!/usr/bin/env python3
"""分布式爬虫系统完整测试套件"""
import os
import sys
import time
import asyncio
from datetime import datetime
from colorama import init, Fore, Back, Style

# 初始化颜色输出
init(autoreset=True)

def print_header(text):
    """打印测试头部"""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.YELLOW}🚀 {text}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")

def print_success(text):
    """打印成功信息"""
    print(f"{Fore.GREEN}✅ {text}{Style.RESET_ALL}")

def print_error(text):
    """打印错误信息"""
    print(f"{Fore.RED}❌ {text}{Style.RESET_ALL}")

def print_warning(text):
    """打印警告信息"""
    print(f"{Fore.YELLOW}⚠️  {text}{Style.RESET_ALL}")

def run_test(test_name, test_func, *args, **kwargs):
    """运行单个测试"""
    print(f"\n{Fore.BLUE}[测试] {test_name}{Style.RESET_ALL}")
    start_time = time.time()
    
    try:
        if asyncio.iscoroutinefunction(test_func):
            # 处理异步函数
            result = asyncio.run(test_func(*args, **kwargs))
        else:
            # 处理同步函数
            result = test_func(*args, **kwargs)
        
        elapsed = time.time() - start_time
        print_success(f"{test_name} - 通过 ({elapsed:.2f}秒)")
        return True, elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        print_error(f"{test_name} - 失败: {e} ({elapsed:.2f}秒)")
        return False, elapsed

def test_config_module():
    """测试配置模块"""
    print_header("测试配置模块")
    
    # 添加项目路径
    sys.path.append('.')
    
    from shared.config import Config
    
    tests = [
        ("基础配置", lambda: Config.REDIS_HOST is not None),
        ("Redis URL", lambda: Config.get_redis_url().startswith("redis://")),
        ("MySQL配置", lambda: isinstance(Config.get_mysql_config(), dict)),
        ("MinIO配置", lambda: isinstance(Config.get_minio_config(), dict)),
        ("日志级别", lambda: Config.LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    ]
    
    results = []
    for name, test in tests:
        success, elapsed = run_test(name, test)
        results.append((name, success, elapsed))
    
    return results

def test_constants_module():
    """测试常量模块"""
    print_header("测试常量模块")
    
    from shared.constants import REDIS_KEYS, ERROR_CODES, USER_AGENTS
    
    tests = [
        ("Redis键常量", lambda: len(REDIS_KEYS) > 10),
        ("错误码", lambda: 1000 in ERROR_CODES and ERROR_CODES[1000] == "成功"),
        ("用户代理", lambda: len(USER_AGENTS) > 5),
        ("Redis键格式化", lambda: REDIS_KEYS["NODE_INFO"].format(node_id="test") == "node:test:info"),
    ]
    
    results = []
    for name, test in tests:
        success, elapsed = run_test(name, test)
        results.append((name, success, elapsed))
    
    return results

def test_models_module():
    """测试数据模型模块"""
    print_header("测试数据模型模块")
    
    from datetime import datetime
    from shared.models import NewsItem, CreateTaskRequest, CrawlerTask
    
    tests = [
        ("NewsItem创建", lambda: NewsItem(
            title="测试标题",
            content="测试内容",
            source="测试源",
            original_url="https://example.com"
        )),
        ("CreateTaskRequest创建", lambda: CreateTaskRequest(
            spider_name="test_spider",
            urls=["https://example.com"]
        )),
        ("CrawlerTask创建", lambda: CrawlerTask(
            task_id="test_task",
            spider_name="test_spider",
            urls=["https://example.com"]
        )),
        ("URL验证", lambda: CreateTaskRequest(
            spider_name="test",
            urls=["https://valid.com"]
        ) and not CreateTaskRequest(spider_name="test", urls=["invalid-url"])),
    ]
    
    results = []
    for name, test in tests:
        success, elapsed = run_test(name, test)
        results.append((name, success, elapsed))
    
    return results

def test_node_manager():
    """测试节点管理器"""
    print_header("测试节点管理器")
    
    # 这里我们导入测试函数，而不是直接运行
    from text import test_node_basic
    
    results = []
    success, elapsed = run_test("节点管理器基本功能", test_node_basic)
    results.append(("节点管理器基本功能", success, elapsed))
    
    return results

def test_imports():
    """测试所有模块导入"""
    print_header("测试模块导入")
    
    modules = [
        ("shared.config", lambda: __import__("shared.config")),
        ("shared.models", lambda: __import__("shared.models")),
        ("shared.constants", lambda: __import__("shared.constants")),
        ("crawler_nodes.node_manager", lambda: __import__("crawler_nodes.node_manager")),
    ]
    
    results = []
    for module_name, import_func in modules:
        success, elapsed = run_test(f"导入 {module_name}", import_func)
        results.append((f"导入 {module_name}", success, elapsed))
    
    return results

def main():
    """主测试函数"""
    print_header("分布式爬虫系统测试套件")
    print(f"{Fore.WHITE}开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"工作目录: {os.getcwd()}")
    print(f"Python版本: {sys.version.split()[0]}")
    
    # 添加项目路径
    sys.path.append('.')
    
    all_results = []
    total_start_time = time.time()
    
    # 运行所有测试组
    test_groups = [
        ("模块导入测试", test_imports),
        ("配置模块测试", test_config_module),
        ("常量模块测试", test_constants_module),
        ("数据模型测试", test_models_module),
        ("节点管理器测试", test_node_manager),
    ]
    
    for group_name, test_func in test_groups:
        print(f"\n{Fore.MAGENTA}▶️  开始: {group_name}{Style.RESET_ALL}")
        try:
            results = test_func()
            all_results.extend(results)
        except Exception as e:
            print_error(f"{group_name} 执行失败: {e}")
    
    # 生成测试报告
    total_elapsed = time.time() - total_start_time
    print_header("测试报告")
    
    total_tests = len(all_results)
    passed_tests = sum(1 for _, success, _ in all_results if success)
    failed_tests = total_tests - passed_tests
    
    # 打印详细结果
    print(f"\n{Fore.WHITE}详细结果:{Style.RESET_ALL}")
    for name, success, elapsed in all_results:
        status = f"{Fore.GREEN}通过" if success else f"{Fore.RED}失败"
        print(f"  {status}{Style.RESET_ALL} - {name} ({elapsed:.2f}秒)")
    
    # 打印统计信息
    print(f"\n{Fore.WHITE}统计信息:{Style.RESET_ALL}")
    print(f"  总测试数: {total_tests}")
    print(f"  通过数: {passed_tests}")
    print(f"  失败数: {failed_tests}")
    print(f"  成功率: {passed_tests/total_tests*100:.1f}%")
    print(f"  总耗时: {total_elapsed:.2f}秒")
    
    # 最终结论
    print_header("测试结论")
    if failed_tests == 0:
        print_success("🎉 所有测试通过！系统准备就绪。")
        return 0
    else:
        print_error(f"⚠️  有 {failed_tests} 项测试失败，请检查问题。")
        
        # 打印失败详情
        print(f"\n{Fore.YELLOW}失败详情:{Style.RESET_ALL}")
        for name, success, _ in all_results:
            if not success:
                print(f"  ❌ {name}")
        
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_error("\n测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print_error(f"测试套件执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)