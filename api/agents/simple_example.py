"""
简单示例 - 展示自然语言交流的具体实现

这个示例清晰地展示了：
1. market_collector 和 roostoo_client 的关系（不重复）
2. 自然语言交流的具体形式
3. 完整的交互流程
"""

import time
from api.agents.manager import AgentManager
from api.agents.market_collector import MarketDataCollector
from api.agents.prompt_manager import PromptManager
from api.agents.executor import TradeExecutor


def demonstrate_architecture():
    """
    演示架构：说明market_collector和roostoo_client的关系
    """
    print("=" * 80)
    print("架构说明：market_collector vs roostoo_client")
    print("=" * 80)
    print("""
    roostoo_client (底层):
    ├── 功能：HTTP请求、认证、返回原始JSON数据
    ├── 职责：与Roostoo API通信
    └── 示例：client.get_ticker("BTC/USD") 
        返回: {"data": {"price": "45000", "volume": "1234", ...}}
    
    market_collector (上层):
    ├── 功能：使用roostoo_client获取数据 → 格式化 → 发布到消息总线
    ├── 职责：定期采集、数据转换、消息传递
    └── 流程：
        1. 调用 roostoo_client.get_ticker()
        2. 使用 DataFormatter 格式化
        3. 发布到 MessageBus (topic: "market_ticks")
    
    关系：market_collector 依赖 roostoo_client，不重复！
    """)
    print("=" * 80)
    print()


def demonstrate_natural_language():
    """
    演示自然语言交流的具体形式
    """
    print("=" * 80)
    print("自然语言交流示例")
    print("=" * 80)
    
    # 1. 创建PromptManager
    pm = PromptManager()
    
    # 2. 系统提示词（定义Agent角色）- 这是自然语言
    print("\n[1] 系统提示词（System Prompt）- 定义Agent角色：")
    print("-" * 80)
    system_prompt = pm.get_system_prompt(
        agent_name="TradingAgent",
        trading_strategy="Focus on trend following and risk management",
        risk_level="moderate"
    )
    print(system_prompt)
    print()
    
    # 3. 模拟市场数据
    print("[2] 模拟市场数据（会被格式化为自然语言）：")
    print("-" * 80)
    from api.agents.data_formatter import DataFormatter
    formatter = DataFormatter()
    
    # 模拟ticker数据
    mock_ticker = {
        "type": "ticker",
        "pair": "BTC/USD",
        "price": 45000.0,
        "volume_24h": 1234567.89,
        "change_24h": 2.5,
        "high_24h": 46000.0,
        "low_24h": 44000.0
    }
    
    # 模拟balance数据
    mock_balance = {
        "type": "balance",
        "total_balance": 10000.0,
        "available_balance": 8000.0,
        "currencies": {
            "USD": {"available": 8000.0, "locked": 0.0, "total": 8000.0},
            "BTC": {"available": 0.1, "locked": 0.0, "total": 0.1}
        }
    }
    
    snapshot = formatter.create_market_snapshot(
        ticker=mock_ticker,
        balance=mock_balance
    )
    
    # 格式化为自然语言文本
    market_text = formatter.format_for_llm(snapshot)
    print(market_text)
    print()
    
    # 4. 创建交易提示词（用户输入）- 这是自然语言
    print("[3] 交易提示词（User Prompt）- 用户给Agent的指令：")
    print("-" * 80)
    trading_prompt = pm.create_trading_prompt(
        market_snapshot=snapshot,
        additional_context="Market is showing upward trend. Consider entry."
    )
    print(trading_prompt)
    print()
    
    # 5. Agent的回复（LLM生成）- 这也是自然语言
    print("[4] Agent的决策回复（Agent Response）- LLM生成的自然语言：")
    print("-" * 80)
    print("""
    示例回复1（买入）:
    "Based on the current market analysis:
    - BTC/USD is at $45,000, up 2.5% in 24h
    - Volume is healthy at 1.23M
    - Price is in the middle of 24h range ($44k-$46k)
    - Account has $8,000 available
    
    Recommendation: buy 0.01 BTC/USD
    Reasoning: The upward trend and positive momentum suggest a good entry point.
    Risk: Moderate - set stop loss at $44,500"
    
    示例回复2（持有）:
    "Current market analysis:
    - BTC/USD at $45,000, slight increase of 2.5%
    - Volume is moderate
    - Price action is consolidating
    
    Recommendation: hold
    Reasoning: Market is in consolidation phase. Wait for clearer trend signal.
    Risk: Low - no action reduces exposure."
    
    示例回复3（卖出）:
    "Market analysis:
    - BTC/USD at $45,000, but showing signs of resistance
    - Volume decreasing
    - Price near 24h high
    
    Recommendation: sell 0.05 BTC/USD at 45000
    Reasoning: Taking profit at resistance level. Risk management suggests reducing position.
    Risk: Low - profit taking at good level."
    """)
    print()
    
    print("=" * 80)
    print()


def run_simple_example():
    """
    运行一个简单的完整示例
    """
    print("=" * 80)
    print("完整交互流程示例")
    print("=" * 80)
    print()
    
    # 1. 初始化
    print("[步骤1] 初始化系统组件...")
    mgr = AgentManager()
    pm = PromptManager()
    
    # 2. 创建Agent（使用自然语言系统提示）
    print("[步骤2] 创建AI Agent...")
    system_prompt = pm.get_system_prompt(
        agent_name="SimpleTradingAgent",
        risk_level="moderate"
    )
    mgr.add_agent(name="simple_agent", system_prompt=system_prompt)
    mgr.start()
    print("✓ Agent已启动")
    
    # 3. 启动数据采集器
    print("[步骤3] 启动市场数据采集器...")
    collector = MarketDataCollector(
        bus=mgr.bus,
        market_topic=mgr.market_topic,
        pairs=["BTC/USD"],
        collect_interval=3.0,  # 3秒采集一次（示例用）
        collect_balance=True,
        collect_ticker=True
    )
    collector.start()
    print("✓ 数据采集器已启动")
    
    # 4. 等待数据采集
    print("[步骤4] 等待市场数据采集（5秒）...")
    time.sleep(5)
    
    # 5. 获取市场快照并创建自然语言提示
    print("[步骤5] 获取市场数据并创建交易提示...")
    snapshot = collector.get_latest_snapshot()
    
    if snapshot and snapshot.get("ticker"):
        # 创建自然语言交易提示
        trading_prompt = pm.create_trading_prompt(
            market_snapshot=snapshot,
            additional_context="This is a test trading request."
        )
        
        print("\n发送给Agent的自然语言提示：")
        print("-" * 80)
        print(trading_prompt)
        print("-" * 80)
        
        # 6. 发送提示给Agent
        print("\n[步骤6] 发送提示给Agent...")
        mgr.broadcast_prompt(role="user", content=trading_prompt)
        print("✓ 提示已发送")
        
        # 7. 等待Agent生成决策
        print("\n[步骤7] 等待Agent生成决策（3秒）...")
        time.sleep(3)
        
        # 8. 收集决策
        print("[步骤8] 收集Agent的决策...")
        decisions = mgr.collect_decisions(max_items=1, wait_seconds=2.0)
        
        if decisions:
            decision = decisions[0]
            print("\nAgent返回的自然语言决策：")
            print("-" * 80)
            print(f"Agent: {decision.get('agent', 'unknown')}")
            print(f"Decision: {decision.get('decision', 'N/A')}")
            print("-" * 80)
        else:
            print("⚠ 未收到决策（可能需要更多时间）")
    else:
        print("⚠ 未获取到市场数据（可能是API问题）")
    
    # 9. 清理
    print("\n[步骤9] 关闭系统...")
    collector.stop()
    collector.join(timeout=2)
    mgr.stop()
    print("✓ 系统已关闭")
    
    print("\n" + "=" * 80)
    print("示例完成！")
    print("=" * 80)


if __name__ == "__main__":
    # 1. 展示架构关系
    demonstrate_architecture()
    
    # 2. 展示自然语言形式
    demonstrate_natural_language()
    
    # 3. 运行完整示例（可选，需要API配置）
    print("\n是否运行完整示例？需要配置Roostoo API密钥。")
    print("取消注释下面的代码来运行：")
    print("# run_simple_example()")
    
    # 取消注释以运行完整示例
    # run_simple_example()

