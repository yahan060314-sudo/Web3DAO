cat > fixed_example_run.py << 'EOF'
import time
from typing import Dict
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.agents.manager import AgentManager
from api.agents.executor import TradeExecutor
from api.roostoo_client import RoostooClient
from api.prompts.prompt_manager import PromptManager

def main():
    mgr = AgentManager()
    
    # 使用 PromptManager 获取详细的现货交易 prompts
    prompt_manager = PromptManager()
    
    # 为 alpha_agent 创建详细的中文现货交易 prompt
    alpha_prompt = prompt_manager.get_system_prompt(
        agent_name="Alpha Agent",
        trading_strategy="保守趋势跟踪，关注风险管理",
        risk_level="conservative"
    )
    
    # 为 beta_agent 创建详细的中文现货交易 prompt  
    beta_prompt = prompt_manager.get_system_prompt(
        agent_name="Beta Agent", 
        trading_strategy="积极动量交易，寻找突破机会",
        risk_level="moderate"
    )
    
    print(f"Alpha Prompt 长度: {len(alpha_prompt)}")
    print(f"Beta Prompt 长度: {len(beta_prompt)}")
    
    # 添加 agents（使用详细的 prompts）
    mgr.add_agent(name="alpha_agent", system_prompt=alpha_prompt)
    mgr.add_agent(name="beta_agent", system_prompt=beta_prompt)

    # 启动 agents
    mgr.start()

    # 启动执行器
    executor = TradeExecutor(bus=mgr.bus, decision_topic=mgr.decision_topic, default_pair="BTC/USD")
    executor.start()

    # 初始对话 - 要求 JSON 格式
    json_instruction = "请以JSON格式输出你的交易决策，包含action、symbol、reason、confidence等字段。"
    mgr.broadcast_prompt(role="user", content=f"Team, analyze BTC and propose next action. {json_instruction}")

    # 对接 Roostoo 实时行情
    client = RoostooClient()
    pair = "BTC/USD"
    poll_seconds = 5

    print("--- Starting real-time market polling from Roostoo ---")
    try:
        for _ in range(12):
            try:
                ticker = client.get_ticker(pair=pair)
                mgr.broadcast_market({"pair": pair, "raw": ticker, "ts": time.time()})
            except Exception as e:
                print(f"[Runner] Error fetching ticker: {e}")
            time.sleep(poll_seconds)

        # 收集决策
        decisions = mgr.collect_decisions(max_items=20, wait_seconds=2.0)
        for d in decisions:
            print(d)
    finally:
        executor.stop()
        executor.join(timeout=2)
        mgr.stop()

if __name__ == "__main__":
    main()
EOF

python fixed_example_run.py
