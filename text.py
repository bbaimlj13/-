#!/usr/bin/env python3
"""测试节点管理器基本功能"""
import asyncio
import sys
sys.path.append('.')
from crawler_nodes.node_manager import CrawlerNode

async def test_node_basic():
    print("=== 节点管理器基本测试 ===")
    
    # 测试1：使用自定义节点ID
    print("1. 测试自定义节点ID...")
    custom_node = CrawlerNode(node_id="test_node_001")
    print(f"   自定义节点ID: {custom_node.node_id}")
    assert custom_node.node_id == "test_node_001", f"节点ID应为'test_node_001'，实际为'{custom_node.node_id}'"
    print("   ✅ 自定义节点ID测试通过")
    
    # 测试2：自动生成节点ID
    print("2. 测试自动生成节点ID...")
    auto_node = CrawlerNode(node_id=None)  # 不传入节点ID，让系统自动生成
    print(f"   自动生成节点ID: {auto_node.node_id}")
    # 检查自动生成的节点ID格式
    assert auto_node.node_id.startswith("node_"), f"自动生成的节点ID应以'node_'开头，实际为'{auto_node.node_id}'"
    assert len(auto_node.node_id) > len("node_"), "节点ID太短"
    print("   ✅ 自动生成节点ID测试通过")
    
    # 测试系统统计
    print("3. 测试系统统计...")
    stats = custom_node.get_system_stats()
    expected_keys = ["cpu_percent", "memory_percent", "process_memory", 
                     "process_cpu", "thread_count", "open_files", 
                     "connections", "uptime"]
    
    for key in expected_keys:
        assert key in stats, f"缺少统计键: {key}"
    
    print(f"   系统统计键: {list(stats.keys())}")
    print("   ✅ 系统统计测试通过")
    
    # 测试Redis键常量使用
    print("4. 测试Redis键常量使用...")
    from shared.constants import REDIS_KEYS
    
    # 测试节点信息键
    node_key = REDIS_KEYS["NODE_INFO"].format(node_id=custom_node.node_id)
    expected_node_key = f"node:{custom_node.node_id}:info"
    assert node_key == expected_node_key, f"节点键应为'{expected_node_key}'，实际为'{node_key}'"
    print(f"   节点Redis键: {node_key}")
    
    # 测试爬虫节点键
    spider_name = "test_spider"
    spider_node_key = REDIS_KEYS["SPIDER_NODES"].format(spider_name=spider_name)
    expected_spider_key = f"spider_nodes:{spider_name}"
    assert spider_node_key == expected_spider_key, f"爬虫节点键应为'{expected_spider_key}'，实际为'{spider_node_key}'"
    print(f"   爬虫节点Redis键: {spider_node_key}")
    print("   ✅ Redis键常量测试通过")
    
    print("✅ 所有节点管理器基本测试通过")
    return True

if __name__ == "__main__":
    try:
        asyncio.run(test_node_basic())
        print("\n🎉 节点管理器测试全部通过！")
    except AssertionError as e:
        print(f"\n❌ 断言失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)