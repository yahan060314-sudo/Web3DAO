#!/usr/bin/env python3
"""
双AI交易示例
演示如何使用两个AI（Qwen和DeepSeek）进行交易，每个AI分配25000资金
"""
import sys
import os
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from api.agents.bus import MessageBus
from api.agents.manager import AgentManager
from api.agents.market_collector import MarketDataCollector
from api.agents.enhanced_executor import EnhancedTradeExecutor
from api.agents.capital_manager import CapitalManager
from api.roostoo_client import RoostooClient


def main():
    """主函数"""
    print("=" * 80)
    print("双AI交易系统示例")
    print("=" * 80)
    print()
    print("配置:")
    print("  - 初始资金: 50000 USD")
    print("  - Qwen AI: 25000 USD")
    print("  - DeepSeek AI: 25000 USD")
    print("  - 模式: dry_run (测试模式，不会真正下单)")
    print()
    
    # 1. 创建消息总线
    bus = MessageBus()
    print("✓ 消息总线创建成功")
    
    # 2. 创建资本管理器
    capital_manager = CapitalManager(initial_capital=50000.0)
    print("✓ 资本管理器创建成功")
    
    # 3. 为两个AI分配资金
    agent_names = ["qwen_agent", "deepseek_agent"]
    allocations = capital_manager.allocate_equal(agent_names)
    print(f"✓ 资金分配完成: {allocations}")
    capital_manager.print_summary()
    
    # 4. 创建Roostoo客户端
    roostoo_client = RoostooClient()
    print("✓ Roostoo客户端创建成功")
    
    # 5. 创建市场数据采集器（自动发现所有可用交易对）
    collector = MarketDataCollector(
        bus=bus,
        market_topic="market_ticks",
        pairs=None,  # None表示自动发现所有可用交易对
        collect_interval=None,  # None表示根据交易对数量自动计算最优间隔
        collect_balance=True,
        collect_ticker=True,
        auto_discover_pairs=True,  # 自动发现所有可用交易对
        batch_size=3  # 每次循环采集3个交易对（避免单次调用太多API）
    )
    print("✓ 市场数据采集器创建成功（将自动发现所有可用交易对，并自动优化采集间隔）")
    
    # 6. 创建Agent管理器
    manager = AgentManager()
    
    # 添加Qwen Agent
    qwen_system_prompt = """You are a trading assistant using Qwen AI. 
    You have been allocated 25000 USD capital.
    Make trading decisions based on market data. 
    Always respond in JSON format: {"action": "buy|sell|wait", "quantity": 0.01, "symbol": "BTCUSDT"}
    Consider your allocated capital when making decisions."""
    
    manager.add_agent(
        name="qwen_agent",
        system_prompt=qwen_system_prompt,
        llm_provider="qwen",
        allocated_capital=25000.0
    )
    print("✓ Qwen Agent 创建成功")
    
    # 添加DeepSeek Agent
    deepseek_system_prompt = """You are a trading assistant using DeepSeek AI.
    You have been allocated 25000 USD capital.
    Make trading decisions based on market data.
    Always respond in JSON format: {"action": "buy|sell|wait", "quantity": 0.01, "symbol": "BTCUSDT"}
    Consider your allocated capital when making decisions."""
    
    manager.add_agent(
        name="deepseek_agent",
        system_prompt=deepseek_system_prompt,
        llm_provider="deepseek",
        allocated_capital=25000.0
    )
    print("✓ DeepSeek Agent 创建成功")
    
    # 7. 创建增强版执行器
    executor = EnhancedTradeExecutor(
        bus=bus,
        decision_topic=manager.decision_topic,
        default_pair="BTC/USD",
        dry_run=True,  # 测试模式，不会真正下单
        enable_decision_manager=True,
        enable_multi_ai_consensus=True,
        capital_manager=capital_manager
    )
    print("✓ 增强版执行器创建成功")
    
    # 8. 启动所有组件
    print("\n启动所有组件...")
    collector.start()
    manager.start()
    executor.start()
    print("✓ 所有组件已启动")
    
    # 9. 等待采集市场数据
    print("\n等待采集市场数据...")
    time.sleep(6)
    
    # 10. 发送交易提示
    print("\n发送交易提示...")
    manager.broadcast_prompt(
        role="user",
        content="Analyze the current market situation and make a trading decision. Respond in JSON format. Consider your allocated capital (25000 USD) when deciding the position size."
    )
    
    # 11. 等待决策生成和执行
    print("\n等待决策生成和执行...")
    print("(这将等待两个AI分别生成决策，然后执行)")
    time.sleep(20)  # 等待LLM响应和执行
    
    # 12. 获取统计信息
    stats = executor.get_statistics(hours=24)
    print(f"\n执行统计:")
    print(f"  总决策数: {stats.get('total_decisions', 0)}")
    print(f"  成功执行数: {stats.get('success_count', 0)}")
    print(f"  失败执行数: {stats.get('fail_count', 0)}")
    print(f"  成功率: {stats.get('success_rate', 0):.2%}")
    
    # 13. 打印资金分配摘要
    print("\n最终资金分配情况:")
    capital_manager.print_summary()
    
    # 14. 停止所有组件
    print("\n停止所有组件...")
    collector.stop()
    manager.stop()
    executor.stop()
    
    collector.join(timeout=2)
    for agent in manager.agents:
        agent.join(timeout=1)
    executor.join(timeout=2)
    
    print("✓ 所有组件已停止")
    
    print("\n" + "=" * 80)
    print("双AI交易系统示例完成")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

