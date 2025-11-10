"""
增强版交易执行器使用示例
展示如何使用 EnhancedTradeExecutor 进行决策管理和执行
"""
import time
from .bus import MessageBus
from .enhanced_executor import EnhancedTradeExecutor
from .manager import AgentManager


def example_enhanced_executor():
    """示例：使用增强版执行器"""
    print("=" * 80)
    print("增强版交易执行器示例")
    print("=" * 80)
    
    # 1. 创建消息总线
    bus = MessageBus()
    
    # 2. 创建增强版执行器
    executor = EnhancedTradeExecutor(
        bus=bus,
        decision_topic="decisions",
        default_pair="BTC/USD",
        dry_run=True,  # 测试模式，不真正下单
        enable_decision_manager=True,  # 启用决策管理器
        db_path="decisions.db",
        enable_multi_ai_consensus=True  # 启用多AI决策综合
    )
    
    # 3. 启动执行器
    executor.start()
    print("\n✓ 增强版执行器已启动")
    
    # 4. 模拟多个AI的决策
    print("\n模拟多个AI的决策...")
    
    # AI 1 的决策
    decision1 = {
        "agent": "agent1",
        "decision": '{"action": "buy", "quantity": 0.01, "symbol": "BTCUSDT"}',
        "market_snapshot": {
            "ticker": {"price": 50000.0},
            "balance": {}
        },
        "timestamp": time.time(),
        "json_valid": True
    }
    
    # AI 2 的决策
    decision2 = {
        "agent": "agent2",
        "decision": '{"action": "buy", "quantity": 0.02, "symbol": "BTCUSDT"}',
        "market_snapshot": {
            "ticker": {"price": 50000.0},
            "balance": {}
        },
        "timestamp": time.time(),
        "json_valid": True
    }
    
    # AI 3 的决策
    decision3 = {
        "agent": "agent3",
        "decision": '{"action": "sell", "quantity": 0.01, "symbol": "BTCUSDT"}',
        "market_snapshot": {
            "ticker": {"price": 50000.0},
            "balance": {}
        },
        "timestamp": time.time(),
        "json_valid": True
    }
    
    # 发布决策
    bus.publish("decisions", decision1)
    time.sleep(0.5)
    bus.publish("decisions", decision2)
    time.sleep(0.5)
    bus.publish("decisions", decision3)
    
    # 等待处理
    print("\n等待决策处理...")
    time.sleep(3)
    
    # 5. 获取统计信息
    print("\n获取统计信息...")
    stats = executor.get_statistics(hours=24)
    print(f"总决策数: {stats.get('total_decisions', 0)}")
    print(f"成功执行数: {stats.get('success_count', 0)}")
    print(f"失败执行数: {stats.get('fail_count', 0)}")
    print(f"成功率: {stats.get('success_rate', 0):.2%}")
    print(f"平均执行时间: {stats.get('avg_execution_time', 0):.3f}秒")
    
    # 6. 停止执行器
    executor.stop()
    print("\n✓ 执行器已停止")


def example_with_agent_manager():
    """示例：与 AgentManager 集成使用"""
    print("=" * 80)
    print("与 AgentManager 集成示例")
    print("=" * 80)
    
    # 1. 创建 AgentManager
    manager = AgentManager()
    
    # 2. 创建增强版执行器
    executor = EnhancedTradeExecutor(
        bus=manager.bus,
        decision_topic=manager.decision_topic,
        default_pair="BTC/USD",
        dry_run=True,
        enable_decision_manager=True,
        enable_multi_ai_consensus=True
    )
    
    # 3. 添加Agent
    manager.add_agent(
        name="TradingAgent1",
        system_prompt="You are a trading assistant. Make trading decisions based on market data."
    )
    
    # 4. 启动所有组件
    manager.start()
    executor.start()
    
    print("\n✓ 所有组件已启动")
    
    # 5. 模拟市场数据
    market_data = {
        "type": "ticker",
        "pair": "BTC/USD",
        "price": 50000.0,
        "volume_24h": 1000000.0,
        "change_24h": 2.5,
        "timestamp": time.time()
    }
    
    manager.broadcast_market(market_data)
    
    # 6. 发送交易提示
    manager.broadcast_prompt(
        role="user",
        content="Analyze the current market situation and make a trading decision."
    )
    
    # 7. 等待决策生成和执行
    print("\n等待决策生成和执行...")
    time.sleep(5)
    
    # 8. 获取统计信息
    stats = executor.get_statistics()
    print(f"\n统计信息: {stats}")
    
    # 9. 停止所有组件
    manager.stop()
    executor.stop()
    print("\n✓ 所有组件已停止")


if __name__ == "__main__":
    try:
        # 运行示例1
        example_enhanced_executor()
        
        # 运行示例2
        # example_with_agent_manager()
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()

