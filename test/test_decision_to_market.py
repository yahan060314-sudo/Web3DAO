#!/usr/bin/env python3
"""
测试"把决策传给市场"功能
"""
import time
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api.agents.bus import MessageBus
from api.agents.enhanced_executor import EnhancedTradeExecutor


def test_dry_run():
    """测试dry_run模式（不会真正下单）"""
    print("=" * 80)
    print("测试1: dry_run模式（不会真正下单）")
    print("=" * 80)
    
    bus = MessageBus()
    executor = EnhancedTradeExecutor(
        bus=bus,
        decision_topic="decisions",
        default_pair="BTC/USD",
        dry_run=True,  # 测试模式，不会真正下单
        enable_decision_manager=True,
        db_path="test_decisions.db",
        enable_multi_ai_consensus=True
    )
    
    executor.start()
    print("✓ 执行器已启动（dry_run模式）")
    
    # 模拟决策
    decision = {
        "agent": "test_agent",
        "decision": '{"action": "buy", "quantity": 0.01, "symbol": "BTCUSDT"}',
        "market_snapshot": {
            "ticker": {"price": 50000.0},
            "balance": {}
        },
        "timestamp": time.time(),
        "json_valid": True
    }
    
    bus.publish("decisions", decision)
    print("✓ 决策已发布")
    
    time.sleep(2)
    
    stats = executor.get_statistics()
    print(f"✓ 统计信息: {stats}")
    
    executor.stop()
    print("✓ 测试完成\n")


def test_api_connection():
    """测试API连接"""
    print("=" * 80)
    print("测试2: API连接测试")
    print("=" * 80)
    
    try:
        from api.roostoo_client import RoostooClient
        
        client = RoostooClient()
        print(f"✓ API URL: {client.base_url}")
        
        if client.api_key:
            print(f"✓ API Key: {client.api_key[:10]}...")
        else:
            print("✗ API Key: Not set")
            return False
        
        try:
            server_time = client.check_server_time()
            print(f"✓ API连接成功: {server_time}")
            return True
        except Exception as e:
            print(f"✗ API连接失败: {e}")
            print("  提示: 如果使用mock API，这是正常的（mock API可能不可用）")
            return False
    except Exception as e:
        print(f"✗ 初始化RoostooClient失败: {e}")
        return False


def test_decision_parsing():
    """测试决策解析"""
    print("=" * 80)
    print("测试3: 决策解析测试")
    print("=" * 80)
    
    from api.agents.enhanced_executor import EnhancedTradeExecutor
    from api.agents.bus import MessageBus
    
    bus = MessageBus()
    executor = EnhancedTradeExecutor(
        bus=bus,
        decision_topic="decisions",
        default_pair="BTC/USD",
        dry_run=True,
        enable_decision_manager=False  # 不需要数据库
    )
    
    # 测试JSON格式决策
    json_decision = {
        "agent": "test_agent",
        "decision": '{"action": "buy", "quantity": 0.01, "symbol": "BTCUSDT"}',
        "timestamp": time.time(),
        "json_valid": True
    }
    
    parsed = executor._parse_decision(json_decision)
    if parsed:
        print(f"✓ JSON决策解析成功: {parsed}")
    else:
        print("✗ JSON决策解析失败")
        return False
    
    # 测试自然语言决策
    nl_decision = {
        "agent": "test_agent",
        "decision": "buy 0.01 BTC",
        "timestamp": time.time(),
        "json_valid": False
    }
    
    parsed = executor._parse_decision(nl_decision)
    if parsed:
        print(f"✓ 自然语言决策解析成功: {parsed}")
    else:
        print("✗ 自然语言决策解析失败")
        return False
    
    return True


def test_multiple_decisions():
    """测试多个决策"""
    print("=" * 80)
    print("测试4: 多决策测试")
    print("=" * 80)
    
    bus = MessageBus()
    executor = EnhancedTradeExecutor(
        bus=bus,
        decision_topic="decisions",
        default_pair="BTC/USD",
        dry_run=True,
        enable_decision_manager=True,
        enable_multi_ai_consensus=True
    )
    
    executor.start()
    print("✓ 执行器已启动")
    
    # 发布多个决策
    decisions = [
        {
            "agent": "agent1",
            "decision": '{"action": "buy", "quantity": 0.01, "symbol": "BTCUSDT"}',
            "market_snapshot": {"ticker": {"price": 50000.0}},
            "timestamp": time.time(),
            "json_valid": True
        },
        {
            "agent": "agent2",
            "decision": '{"action": "buy", "quantity": 0.02, "symbol": "BTCUSDT"}',
            "market_snapshot": {"ticker": {"price": 50000.0}},
            "timestamp": time.time(),
            "json_valid": True
        },
        {
            "agent": "agent3",
            "decision": '{"action": "sell", "quantity": 0.01, "symbol": "BTCUSDT"}',
            "market_snapshot": {"ticker": {"price": 50000.0}},
            "timestamp": time.time(),
            "json_valid": True
        }
    ]
    
    for i, decision in enumerate(decisions, 1):
        bus.publish("decisions", decision)
        print(f"✓ 决策 {i} 已发布")
        time.sleep(0.5)
    
    time.sleep(3)
    
    stats = executor.get_statistics()
    print(f"✓ 统计信息: {stats}")
    
    executor.stop()
    print("✓ 测试完成\n")


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("测试：把决策传给市场")
    print("=" * 80 + "\n")
    
    # 检查环境变量
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️ 警告: .env 文件不存在")
        print("   请创建 .env 文件并配置 API 凭证")
        print("   示例: ROOSTOO_API_KEY=your_key")
        print()
    
    # 运行测试
    tests = [
        ("决策解析", test_decision_parsing),
        ("dry_run模式", test_dry_run),
        ("API连接", test_api_connection),
        ("多决策", test_multiple_decisions),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            result = test_func()
            results[name] = result if result is not None else True
        except Exception as e:
            print(f"✗ 测试 '{name}' 失败: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False
        print()
    
    # 输出测试结果
    print("=" * 80)
    print("测试结果总结")
    print("=" * 80)
    for name, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")
    
    # 清理测试数据库
    test_db = Path("test_decisions.db")
    if test_db.exists():
        try:
            test_db.unlink()
            print(f"\n✓ 清理测试数据库: {test_db}")
        except Exception as e:
            print(f"\n⚠️ 无法清理测试数据库: {e}")
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断测试")
    except Exception as e:
        print(f"\n\n测试出错: {e}")
        import traceback
        traceback.print_exc()

