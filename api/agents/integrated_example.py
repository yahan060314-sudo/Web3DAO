"""
集成示例 - 展示如何使用所有模块进行完整的交易流程

这个示例展示了：
1. 从API获取初始本金并均分给两个Agent
2. 如何使用MarketDataCollector采集Roostoo数据
3. 如何使用PromptManager管理prompt
4. 如何创建和运行Agent
5. 如何执行交易决策

运行方式：
    python -m api.agents.integrated_example
"""

import os
import time
from typing import List

from .manager import AgentManager
from .executor import TradeExecutor
from .market_collector import MarketDataCollector
from .prompt_manager import PromptManager
from .capital_manager import CapitalManager
from api.roostoo_client import RoostooClient


def get_initial_capital_from_api() -> float:
    """
    从API获取初始本金
    
    Returns:
        初始本金（USD），如果获取失败则返回默认值50000
    """
    try:
        client = RoostooClient()
        exchange_info = client.get_exchange_info()
        
        # 从API响应中提取InitialWallet
        if isinstance(exchange_info, dict) and "InitialWallet" in exchange_info:
            initial_wallet = exchange_info["InitialWallet"]
            if isinstance(initial_wallet, dict) and "USD" in initial_wallet:
                initial_capital = float(initial_wallet["USD"])
                print(f"[InitialCapital] ✓ 从API获取初始本金: {initial_capital:.2f} USD")
                return initial_capital
        
        # 如果API响应格式不符合预期
        print(f"[InitialCapital] ⚠️ API响应格式不符合预期，使用默认值50000")
        return 50000.0
        
    except Exception as e:
        print(f"[InitialCapital] ⚠️ 从API获取初始本金失败: {e}")
        print(f"[InitialCapital] 使用默认值: 50000.0 USD")
        return 50000.0


def main():
    """
    主函数：完整的交易系统集成示例
    """
    print("=" * 60)
    print("Web3 Quant Trading System - Integrated Example")
    print("=" * 60)
    
    # 0. 获取初始本金并创建资本管理器
    print("\n[0] Getting initial capital and setting up capital manager...")
    initial_capital = get_initial_capital_from_api()
    capital_manager = CapitalManager(initial_capital=initial_capital)
    
    # 1. 初始化消息总线和Agent管理器
    print("\n[1] Initializing Agent Manager...")
    mgr = AgentManager()
    
    # 2. 初始化Prompt管理器
    print("[2] Initializing Prompt Manager...")
    prompt_mgr = PromptManager()
    
    # 3. 创建Agent并配置系统prompt
    print("[3] Creating AI Agents...")
    
    # Agent 1: 保守型交易Agent
    conservative_prompt = prompt_mgr.get_system_prompt(
        agent_name="ConservativeAgent",
        trading_strategy="Focus on capital preservation. Only trade on strong signals.",
        risk_level="conservative"
    )
    
    # Agent 2: 平衡型交易Agent
    balanced_prompt = prompt_mgr.get_system_prompt(
        agent_name="BalancedAgent",
        trading_strategy="Balance risk and reward. Look for good opportunities.",
        risk_level="moderate"
    )
    
    # 3.5. 均分本金给两个Agent（只在开始时分配一次）
    print("\n[3.5] Allocating capital to agents...")
    agent_names = ["conservative_agent", "balanced_agent"]
    allocations = capital_manager.allocate_equal(agent_names)
    capital_manager.print_summary()
    
    # 为每个Agent分配资金额度
    conservative_capital = allocations.get("conservative_agent", initial_capital / 2)
    balanced_capital = allocations.get("balanced_agent", initial_capital / 2)
    
    # 添加Agent并传入分配的资金额度
    mgr.add_agent(
        name="conservative_agent", 
        system_prompt=conservative_prompt,
        allocated_capital=conservative_capital
    )
    mgr.add_agent(
        name="balanced_agent", 
        system_prompt=balanced_prompt,
        allocated_capital=balanced_capital
    )
    
    # 注意：两个Agent现在独立运行，各自管理自己的资金
    # 资金分配只在开始时进行一次，之后两个Agent的操作完全独立
    
    # 4. 启动Agent
    print("[4] Starting Agents...")
    mgr.start()
    
    # 5. 创建并启动市场数据采集器
    print("[5] Starting Market Data Collector...")
    collector = MarketDataCollector(
        bus=mgr.bus,
        market_topic=mgr.market_topic,
        pairs=["BTC/USD"],  # 可以添加更多交易对
        collect_interval=5.0,  # 每5秒采集一次
        collect_balance=True,
        collect_ticker=True
    )
    collector.start()
    
    # 6. 创建并启动交易执行器
    print("[6] Starting Trade Executor...")
    # 检查是否使用dry_run模式（可以通过环境变量控制）
    import os
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    
    executor = TradeExecutor(
        bus=mgr.bus,
        decision_topic=mgr.decision_topic,
        default_pair="BTC/USD",
        dry_run=dry_run  # 默认False（真实交易），可通过环境变量DRY_RUN=true设置为测试模式
    )
    executor.start()
    
    # 7. 等待市场数据采集（让系统先获取一些数据）
    print("\n[7] Waiting for initial market data...")
    time.sleep(8)  # 等待至少一次数据采集
    
    # 8. 发送初始交易提示
    print("\n[8] Sending initial trading prompts...")
    
    # 获取最新市场快照
    market_snapshot = collector.get_latest_snapshot()
    
    # 使用PromptManager创建交易提示
    trading_prompt = prompt_mgr.create_trading_prompt(
        market_snapshot=market_snapshot,
        additional_context="This is the initial trading decision request. Analyze the market and provide your recommendation."
    )
    
    # 广播提示给所有Agent
    mgr.broadcast_prompt(role="user", content=trading_prompt)
    
    # 9. 运行主循环
    print("\n[9] Running main trading loop...")
    print("=" * 60)
    print("System is now running. Press Ctrl+C to stop.")
    print("=" * 60)
    
    try:
        # 运行一段时间（示例：2分钟）
        run_duration = 120
        start_time = time.time()
        
        while time.time() - start_time < run_duration:
            # 每30秒发送一次新的交易提示
            time.sleep(30)
            
            # 获取最新市场快照
            market_snapshot = collector.get_latest_snapshot()
            
            # 创建新的交易提示
            trading_prompt = prompt_mgr.create_trading_prompt(
                market_snapshot=market_snapshot,
                additional_context="Periodic market analysis request."
            )
            
            # 广播提示
            mgr.broadcast_prompt(role="user", content=trading_prompt)
            print(f"\n[{time.strftime('%H:%M:%S')}] Sent periodic trading prompt")
            
            # 收集并显示最近的决策
            decisions = mgr.collect_decisions(max_items=5, wait_seconds=2.0)
            if decisions:
                print(f"  Recent decisions ({len(decisions)}):")
                for d in decisions[-3:]:  # 只显示最后3个
                    print(f"    - {d.get('agent', 'unknown')}: {d.get('decision', 'N/A')[:80]}")
        
    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user")
    
    # 10. 优雅关闭
    print("\n[10] Shutting down...")
    collector.stop()
    collector.join(timeout=2)
    executor.stop()
    executor.join(timeout=2)
    mgr.stop()
    
    # 收集最终决策
    print("\n[11] Final decisions summary:")
    final_decisions = mgr.collect_decisions(max_items=20, wait_seconds=1.0)
    for i, d in enumerate(final_decisions, 1):
        print(f"  {i}. [{d.get('agent', 'unknown')}] {d.get('decision', 'N/A')[:100]}")
    
    print("\n" + "=" * 60)
    print("System shutdown complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()

