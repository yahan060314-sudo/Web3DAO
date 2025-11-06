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

