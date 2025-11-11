import time
from typing import Dict

from .manager import AgentManager
from .executor import TradeExecutor
from api.roostoo_client import RoostooClient
from config.config import DEFAULT_REQUEST_TIMEOUT_SECONDS, TRADE_INTERVAL_SECONDS


def main():
    mgr = AgentManager()
    # 添加两个示例 Agent，它们共享同一个总线，可以互相感知对话与市场数据
    mgr.add_agent(name="alpha_agent", system_prompt="You are Alpha. Propose cautious trading suggestions.")
    mgr.add_agent(name="beta_agent", system_prompt="You are Beta. Emphasize risk and capital preservation.")

    # 启动 agents
    mgr.start()

    # 启动执行器（订阅决策并下单，遵守 1/min）
    executor = TradeExecutor(bus=mgr.bus, decision_topic=mgr.decision_topic, default_pair="BTC/USD")
    executor.start()

    # 初始对话
    mgr.broadcast_prompt(role="user", content="Team, analyze BTC and propose next action (buy/sell/hold).")

    # 对接 Roostoo 实时行情：以固定间隔轮询 ticker 并广播
    client = RoostooClient()
    pair = "BTC/USD"
    poll_seconds = 5  # 行情轮询频率（不涉及下单限频）

    print("--- Starting real-time market polling from Roostoo ---")
    try:
        for _ in range(12):  # 示例跑大约 1 分钟
            try:
                ticker = client.get_ticker(pair=pair)
                # 统一广播结构（简化：直接广播原始返回）
                mgr.broadcast_market({"pair": pair, "raw": ticker, "ts": time.time()})
            except Exception as e:
                print(f"[Runner] Error fetching ticker: {e}")
            time.sleep(poll_seconds)

        # 收集一段时间内的决策
        decisions = mgr.collect_decisions(max_items=20, wait_seconds=2.0)
        for d in decisions:
            print(d)
    finally:
        # 优雅停止
        executor.stop()
        executor.join(timeout=2)
        mgr.stop()


if __name__ == "__main__":
    main()

