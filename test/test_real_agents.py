#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实 Agent 测试：测试 agent1 和 agent2 是否能接收消息并做出决策
"""
import os
import sys
import time
import threading
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

# 硬编码测试 API 凭证（如果需要）
if not os.getenv("ROOSTOO_API_KEY"):
    os.environ["ROOSTOO_API_KEY"] = "test_key"
    os.environ["ROOSTOO_SECRET_KEY"] = "test_secret"
    os.environ["ROOSTOO_API_URL"] = "https://mock-api.roostoo.com"
    os.environ["DRY_RUN"] = "true"

from api.agents.manager import AgentManager
from api.agents.capital_manager import CapitalManager
from api.agents.position_tracker import PositionTracker
from api.agents.prompt_manager import PromptManager

def monitor_decisions(bus, decision_topic, duration=30):
    """
    监控决策消息
    """
    print(f"[Monitor] 🔍 开始监听决策消息（{duration}秒）...")
    decision_sub = bus.subscribe(decision_topic)
    decisions = []
    start_time = time.time()
    
    while time.time() - start_time < duration:
        decision_msg = decision_sub.recv(timeout=1.0)
        if decision_msg is not None:
            agent_name = decision_msg.get("agent", "unknown")
            decision_text = decision_msg.get("decision", "")
            decisions.append(decision_msg)
            print(f"[Monitor] ✓ 收到决策: {agent_name}")
            print(f"[Monitor] 决策内容（前150字符）: {decision_text[:150]}...")
        else:
            elapsed = int(time.time() - start_time)
            if elapsed % 5 == 0:
                print(f"[Monitor] ⏳ 等待决策中... ({elapsed}/{duration}秒)")
    
    return decisions

def test_real_agents():
    """
    测试真实 Agent
    """
    print("=" * 80)
    print("真实 Agent 消息接收和决策测试")
    print("=" * 80)
    
    try:
        # 1. 创建组件
        print("\n[1] 创建组件...")
        capital_manager = CapitalManager(initial_capital=50000.0)
        position_tracker = PositionTracker()
        mgr = AgentManager(capital_manager=capital_manager, position_tracker=position_tracker)
        prompt_mgr = PromptManager()
        
        # 2. 分配资金
        print("[2] 分配资金...")
        allocations = capital_manager.allocate_equal(["agent_1", "agent_2"])
        agent_1_capital = allocations.get("agent_1", 25000.0)
        agent_2_capital = allocations.get("agent_2", 25000.0)
        
        position_tracker.initialize_agent("agent_1", agent_1_capital)
        position_tracker.initialize_agent("agent_2", agent_2_capital)
        
        # 3. 创建系统提示词
        print("[3] 创建系统提示词...")
        agent_1_prompt = prompt_mgr.get_system_prompt(
            agent_name="Agent1",
            trading_strategy="Test: Make quick decisions based on market data",
            risk_level="moderate"
        )
        
        agent_2_prompt = prompt_mgr.get_system_prompt(
            agent_name="Agent2",
            trading_strategy="Test: Analyze all trading pairs and make decisions",
            risk_level="moderate"
        )
        
        # 4. 添加 Agent
        print("[4] 添加 Agent...")
        mgr.add_agent(
            name="agent_1",
            system_prompt=agent_1_prompt,
            llm_provider="deepseek",
            allocated_capital=agent_1_capital
        )
        
        mgr.add_agent(
            name="agent_2",
            system_prompt=agent_2_prompt,
            llm_provider="qwen",
            allocated_capital=agent_2_capital
        )
        
        # 5. 启动 Agent
        print("[5] 启动 Agent...")
        mgr.start()
        
        # 等待 Agent 启动
        print("[6] 等待 Agent 启动（3秒）...")
        time.sleep(3)
        
        # 检查 Agent 状态
        print("\n[7] 检查 Agent 状态...")
        for agent in mgr.agents:
            is_alive = agent.is_alive()
            queue_size = agent.market_sub._q.qsize() if hasattr(agent.market_sub._q, 'qsize') else 'N/A'
            print(f"  - {agent.name}: {'运行中' if is_alive else '已停止'}, 队列大小={queue_size}")
        
        # 6. 启动决策监控
        print("\n[8] 启动决策监控...")
        monitor_thread = threading.Thread(
            target=monitor_decisions,
            args=(mgr.bus, mgr.decision_topic, 60),
            daemon=True
        )
        monitor_thread.start()
        
        # 7. 发送测试消息
        print("\n[9] 发送测试消息...")
        
        # 7.1 发送单个 ticker
        print("  [9.1] 发送单个 ticker...")
        ticker_msg = {
            "type": "ticker",
            "pair": "BTC/USD",
            "price": 100000.0,
            "timestamp": time.time()
        }
        mgr.bus.publish(mgr.market_topic, ticker_msg)
        print(f"    ✓ 已发布: {ticker_msg['pair']} = ${ticker_msg['price']}")
        time.sleep(2)
        
        # 7.2 发送完整快照
        print("\n  [9.2] 发送完整市场快照...")
        complete_snapshot = {
            "type": "complete_market_snapshot",
            "is_complete": True,
            "timestamp": time.time(),
            "tickers": {
                "BTC/USD": {"pair": "BTC/USD", "price": 100000.0, "type": "ticker"},
                "ETH/USD": {"pair": "ETH/USD", "price": 3000.0, "type": "ticker"},
                "SOL/USD": {"pair": "SOL/USD", "price": 140.0, "type": "ticker"}
            },
            "balance": {"total_balance": 50000.0},
            "total_pairs_collected": 3,
            "total_pairs_available": 3
        }
        
        print(f"    快照类型: {complete_snapshot['type']}")
        print(f"    is_complete: {complete_snapshot['is_complete']}")
        print(f"    交易对数量: {len(complete_snapshot['tickers'])}")
        
        mgr.bus.publish(mgr.market_topic, complete_snapshot)
        print("    ✓ 完整快照已发布到消息总线")
        
        # 等待 Agent 接收
        print("\n  [9.3] 等待 Agent 接收完整快照（5秒）...")
        time.sleep(5)
        
        # 检查 Agent 状态
        print("\n  [9.4] 检查 Agent 状态...")
        for agent in mgr.agents:
            queue_size = agent.market_sub._q.qsize() if hasattr(agent.market_sub._q, 'qsize') else 'N/A'
            ticker_count = len(agent.current_tickers) if agent.current_tickers else 0
            has_snapshot = agent.last_market_snapshot is not None
            print(f"    - {agent.name}:")
            print(f"      队列大小: {queue_size}")
            print(f"      tickers数量: {ticker_count}")
            print(f"      有快照: {'是' if has_snapshot else '否'}")
            if has_snapshot:
                snapshot_type = agent.last_market_snapshot.get("type", "unknown")
                is_complete = agent.last_market_snapshot.get("is_complete", False)
                print(f"      快照类型: {snapshot_type}, is_complete: {is_complete}")
        
        # 7.5 发送交易提示
        print("\n  [9.5] 发送交易提示，触发决策生成...")
        trading_prompt = """Complete market snapshot with all trading pairs has been collected. Analyze ALL available trading pairs and make a trading decision.

Current Market Data (All Pairs):
- BTC/USD: $100000.0
- ETH/USD: $3000.0
- SOL/USD: $140.0

IMPORTANT: You have access to data from ALL trading pairs. Compare opportunities and select the BEST trading opportunity.

Provide your decision in JSON format."""
        
        mgr.broadcast_prompt(role="user", content=trading_prompt)
        print("    ✓ 交易提示已广播")
        
        # 8. 等待决策
        print("\n[10] 等待 Agent 生成决策（30秒）...")
        time.sleep(30)
        
        # 9. 再次检查状态
        print("\n[11] 再次检查 Agent 状态...")
        for agent in mgr.agents:
            queue_size = agent.market_sub._q.qsize() if hasattr(agent.market_sub._q, 'qsize') else 'N/A'
            ticker_count = len(agent.current_tickers) if agent.current_tickers else 0
            has_snapshot = agent.last_market_snapshot is not None
            print(f"  - {agent.name}:")
            print(f"    队列大小: {queue_size}")
            print(f"    tickers数量: {ticker_count}")
            print(f"    有快照: {'是' if has_snapshot else '否'}")
        
        # 10. 停止 Agent
        print("\n[12] 停止 Agent...")
        mgr.stop()
        time.sleep(2)
        
        print("\n" + "=" * 80)
        print("测试完成")
        print("=" * 80)
        print("\n请查看上面的日志，确认：")
        print("  1. Agent 是否收到了完整快照（应该看到 '🔔 收到完整市场快照消息！'）")
        print("  2. Agent 是否生成了决策（应该看到 '[Monitor] ✓ 收到决策'）")
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保已安装所有依赖: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_real_agents()

