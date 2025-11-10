
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.agents.manager import AgentManager
from api.agents.executor import TradeExecutor
from api.roostoo_client import RoostooClient
from textwrap import dedent
import json
import re

class MiniMaxAgentManager(AgentManager):
    """
    MiniMax 专用的 Agent Manager，添加 JSON 修复功能
    """
    
    def _fix_minimax_decision(self, decision_text):
        """修复 MiniMax 的决策输出"""
        if not decision_text:
            return None
        
        # 尝试直接解析
        try:
            return json.loads(decision_text.strip())
        except:
            pass
        
        # 提取 JSON 部分
        json_match = re.search(r'\{[^{}]*\{[^{}]*\}[^{}]*\}|\{[^{}]*\}', decision_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except:
                pass
        
        return None

def main():
    mgr = MiniMaxAgentManager()
    
    # 使用增强版的 prompt（对 MiniMax 更友好）
    enhanced_prompt = dedent("""
    你是一位加密货币现货交易助手。

    【重要指令】你必须以严格的 JSON 格式输出决策，不要有任何其他文字！

    输出格式必须是：
    {
      "action": "wait | open_long | close_long | hold",
      "symbol": "BTCUSDT",
      "reasoning": "你的分析理由",
      "confidence": 85
    }

    注意：只输出 JSON，不要有其他文字！
    """).strip()

    print(f"✅ 使用增强版 prompt，长度: {len(enhanced_prompt)}")
    
    mgr.add_agent(name="alpha_agent", system_prompt=enhanced_prompt)
    mgr.add_agent(name="beta_agent", system_prompt=enhanced_prompt)

    # 启动 agents
    mgr.start()

    # 启动执行器
    executor = TradeExecutor(bus=mgr.bus, decision_topic=mgr.decision_topic, default_pair="BTC/USD")
    executor.start()

    # 初始对话
    mgr.broadcast_prompt(role="user", content="请分析 BTC 并给出交易决策。只输出 JSON。")

    # 对接 Roostoo 实时行情
    client = RoostooClient()
    pair = "BTC/USD"
    poll_seconds = 5

    print("--- Starting real-time market polling from Roostoo ---")
    try:
        for _ in range(6):  # 缩短测试时间
            try:
                ticker = client.get_ticker(pair=pair)
                mgr.broadcast_market({"pair": pair, "raw": ticker, "ts": time.time()})
            except Exception as e:
                print(f"[Runner] Error fetching ticker: {e}")
            time.sleep(poll_seconds)

        # 收集决策
        decisions = mgr.collect_decisions(max_items=10, wait_seconds=2.0)
        for d in decisions:
            print(d)
    finally:
        executor.stop()
        executor.join(timeout=2)
        mgr.stop()

if __name__ == "__main__":
    main()
