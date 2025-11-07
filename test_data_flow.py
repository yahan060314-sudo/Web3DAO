#!/usr/bin/env python3
"""
测试完整数据流（简化版，不实际执行交易）
"""
import time
from api.agents.manager import AgentManager
from api.agents.market_collector import MarketDataCollector
from api.agents.prompt_manager import PromptManager

print("=" * 60)
print("Testing Complete Data Flow")
print("=" * 60)

# 1. 初始化
print("\n[1] Initializing components...")
mgr = AgentManager()
pm = PromptManager()
print("✓ AgentManager initialized")
print("✓ PromptManager initialized")

# 2. 创建Agent
print("\n[2] Creating test agent...")
system_prompt = pm.get_system_prompt("TestAgent", risk_level="moderate")
mgr.add_agent(name="test_agent", system_prompt=system_prompt)
mgr.start()
print("✓ Test agent created and started")

# 3. 启动数据采集器
print("\n[3] Starting market data collector...")
collector = MarketDataCollector(
    bus=mgr.bus,
    market_topic=mgr.market_topic,
    pairs=["BTC/USD"],
    collect_interval=3.0,  # 3秒采集一次（测试用）
    collect_balance=True,
    collect_ticker=True
)
collector.start()
print("✓ Market data collector started")

# 4. 等待数据采集
print("\n[4] Waiting for market data (10 seconds)...")
time.sleep(10)

# 5. 检查数据
print("\n[5] Checking collected data...")
snapshot = collector.get_latest_snapshot()
if snapshot:
    print("✓ Market snapshot created")
    if snapshot.get("ticker"):
        print("  - Ticker data: ✓")
    if snapshot.get("balance"):
        print("  - Balance data: ✓")
else:
    print("⚠ No market snapshot yet (may need more time)")

# 6. 测试Prompt生成
print("\n[6] Testing prompt generation...")
if snapshot:
    prompt = pm.create_trading_prompt(snapshot)
    print("✓ Trading prompt generated (length:", len(prompt), "chars)")
    
    # 测试组友的模板（如果可用）
    spot_prompt = pm.create_spot_prompt_from_market_data(snapshot)
    if spot_prompt:
        print("✓ Spot trading prompt generated (using teammate's template)")
    else:
        print("⚠ Spot trading prompt not available (using default)")
else:
    print("⚠ Cannot generate prompt (no market data)")

# 7. 检查Agent决策
print("\n[7] Checking agent decisions...")
time.sleep(5)  # 等待Agent处理
decisions = mgr.collect_decisions(max_items=5, wait_seconds=2.0)
if decisions:
    print(f"✓ Received {len(decisions)} decision(s)")
    for i, d in enumerate(decisions, 1):
        print(f"  {i}. Agent: {d.get('agent')}")
        print(f"     Decision: {d.get('decision', 'N/A')[:80]}")
else:
    print("⚠ No decisions received yet")

# 8. 清理
print("\n[8] Cleaning up...")
collector.stop()
collector.join(timeout=2)
mgr.stop()
print("✓ Cleanup complete")

print("\n" + "=" * 60)
print("Data flow test completed!")
print("=" * 60)

