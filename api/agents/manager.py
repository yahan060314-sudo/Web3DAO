import threading
import time
from typing import List, Dict, Any

from .bus import MessageBus
from .base_agent import BaseAgent


class AgentManager:
    """
    负责：
    - 创建并管理多个 Agent 线程
    - 向市场主题广播市场数据（未来可对接 Roostoo）
    - 向对话主题广播提示词
    - 从决策主题收集各 Agent 的决策
    """

    def __init__(self):
        self.bus = MessageBus()
        self.market_topic = "market_ticks"
        self.dialog_topic = "dialog_prompts"
        self.decision_topic = "decisions"
        self.agents: List[BaseAgent] = []
        self._stop = False

    def add_agent(self, name: str, system_prompt: str) -> None:
        agent = BaseAgent(
            name=name,
            bus=self.bus,
            market_topic=self.market_topic,
            dialog_topic=self.dialog_topic,
            decision_topic=self.decision_topic,
            system_prompt=system_prompt,
        )
        self.agents.append(agent)

    def start(self) -> None:
        for a in self.agents:
            a.start()

    def stop(self) -> None:
        self._stop = True
        for a in self.agents:
            a.stop()
        for a in self.agents:
            a.join(timeout=2)

    def broadcast_market(self, snapshot: Dict[str, Any]) -> None:
        self.bus.publish(self.market_topic, snapshot)

    def broadcast_prompt(self, role: str, content: str) -> None:
        self.bus.publish(self.dialog_topic, {"role": role, "content": content})

    def collect_decisions(self, max_items: int = 10, wait_seconds: float = 2.0) -> List[Dict[str, Any]]:
        # 临时订阅决策通道，收集一小段时间内的决策
        sub = self.bus.subscribe(self.decision_topic)
        got: List[Dict[str, Any]] = []
        end = time.time() + wait_seconds
        while len(got) < max_items and time.time() < end:
            msg = sub.recv(timeout=0.2)
            if msg is not None:
                got.append(msg)
        return got

        # ---------- five-day performance review (敲打机制) ----------
    def five_day_review_and_motivation(self) -> Dict[str, Any]:
        """
        Every 5 days:
        - Aggregate total PnL across last 5 daily CSVs.
        - Rank agents.
        - Broadcast personalized motivational prompts.
        """
        today = time.strftime("%Y-%m-%d", time.localtime())
        days = []
        for i in range(5):
            t = time.time() - 86400 * i
            days.append(time.strftime("%Y-%m-%d", time.localtime(t)))

        # Collect 5-day performance
        per_agent_pnl = defaultdict(float)
        for d in days:
            fpath = self.log_dir / f"executions_{d}.csv"
            if not fpath.exists():
                continue
            with fpath.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    agent = r["agent"]
                    pnl = float(r.get("pnl_usd", 0.0) or 0.0)
                    per_agent_pnl[agent] += pnl

        if not per_agent_pnl:
            payload = {"day": today, "summary": {}, "message": "No trades in past 5 days."}
            self.broadcast_prompt("system", payload["message"])
            return payload

        # Sort by total PnL descending
        ranked = sorted(per_agent_pnl.items(), key=lambda x: x[1], reverse=True)
        rank_map = {agent: i+1 for i, (agent, _) in enumerate(ranked)}

        # Build messages
        messages = {}
        for agent, pnl in ranked:
            rank = rank_map[agent]
            if rank == 1:
                msg = (
                    f"🥇 交易员 {agent}：过去5日总收益 {pnl:.2f} USDT，排名第1。\n"
                    "你这几天表现不错，但不要松懈，保持稳健的风控与节奏。"
                )
            else:
                msg = (
                    f"⚙️ 交易员 {agent}：过去5日总收益 {pnl:.2f} USDT，排名第{rank}。\n"
                    "要更加努力，争取成为第一名，但也要注意控制风险，"
                    "取得更优的风险收益比才是最优表现。"
                )
            messages[agent] = msg
            # send individually to each agent
            self.broadcast_prompt(agent, msg)

        # summary broadcast
        summary_lines = [f"{i+1}. {a}: {pnl:.2f}" for i, (a, pnl) in enumerate(ranked)]
        summary_text = "📊 五日表现排名：\n" + "\n".join(summary_lines)
        self.broadcast_prompt("system", summary_text)

        return {
            "day": today,
            "ranking": ranked,
            "messages": messages,
            "summary_text": summary_text,
        }

