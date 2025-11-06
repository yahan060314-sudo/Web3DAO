import threading
import time
from typing import Dict, Any, List, Optional

from api.llm_clients import get_llm_client
from .bus import MessageBus, Subscription


class BaseAgent(threading.Thread):
    """
    通用 Agent 基类：
    - 独立线程运行
    - 订阅市场数据与对话消息
    - 通过 LLM 生成简单决策（占位实现）
    - 将决策发布到决策通道
    """

    def __init__(self,
                 name: str,
                 bus: MessageBus,
                 market_topic: str,
                 dialog_topic: str,
                 decision_topic: str,
                 system_prompt: str,
                 poll_timeout: float = 1.0):
        super().__init__(name=name)
        self.daemon = True
        self.bus = bus
        self.market_sub: Subscription = bus.subscribe(market_topic)
        self.dialog_sub: Subscription = bus.subscribe(dialog_topic)
        self.decision_topic = decision_topic
        self.system_prompt = system_prompt
        self.poll_timeout = poll_timeout
        self._stopped = False
        self.llm = get_llm_client()

        # Agent 内部状态（可扩展）
        self.last_market_snapshot: Optional[Dict[str, Any]] = None
        self.dialog_history: List[Dict[str, str]] = []

    def stop(self):
        self._stopped = True

    def run(self):
        # 主循环：轮询市场数据与对话消息
        while not self._stopped:
            market_msg = self.market_sub.recv(timeout=self.poll_timeout)
            if market_msg is not None:
                self.last_market_snapshot = market_msg

            dialog_msg = self.dialog_sub.recv(timeout=0.01)
            if dialog_msg is not None:
                self._handle_dialog(dialog_msg)

            # 简单节流，避免忙等
            time.sleep(0.01)

    def _handle_dialog(self, msg: Dict[str, Any]) -> None:
        # 将对话消息追加到历史
        role = msg.get("role", "user")
        content = msg.get("content", "")
        self.dialog_history.append({"role": role, "content": content})

        # 构建 LLM 输入：系统提示 + 对话历史 + 市场片段（如有）
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self.system_prompt}
        ] + self.dialog_history[-8:]  # 控制上下文长度

        if self.last_market_snapshot is not None:
            market_text = f"Market: {self.last_market_snapshot}"
            messages.append({"role": "system", "content": market_text})

        # 请求 LLM 得到占位式决策
        llm_out = self.llm.chat(messages, temperature=0.3, max_tokens=256)
        decision_text = llm_out.get("content") or "hold"

        decision = {
            "agent": self.name,
            "decision": decision_text,
            "market": self.last_market_snapshot,
            "ts": time.time()
        }
        self.bus.publish(self.decision_topic, decision)

