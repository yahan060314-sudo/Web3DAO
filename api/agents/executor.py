import threading
import time
import re
from typing import Optional, Dict, Any

from api.roostoo_client import RoostooClient
from .bus import MessageBus
from config.config import TRADE_INTERVAL_SECONDS


class TradeExecutor(threading.Thread):
    """
    订阅决策通道，将自然语言决策转为实际下单动作。
    - 遵守 1/min 的限频（使用 TRADE_INTERVAL_SECONDS = 61）
    - 简单的自然语言解析（buy/sell + 数量，可选价格）
    - 生产中建议改为结构化决策格式
    """

    def __init__(self, bus: MessageBus, decision_topic: str, default_pair: str = "BTC/USD"):
        super().__init__(name="TradeExecutor")
        self.daemon = True
        self.bus = bus
        self.decision_sub = bus.subscribe(decision_topic)
        self.client = RoostooClient()
        self.default_pair = default_pair
        self._stopped = False
        self._last_order_ts: Optional[float] = None

    def stop(self):
        self._stopped = True

    def run(self):
        while not self._stopped:
            msg = self.decision_sub.recv(timeout=0.5)
            if msg is None:
                continue
            try:
                self._maybe_execute(msg)
            except Exception as e:
                # 避免线程崩溃，生产中应使用 logger
                print(f"[Executor] Error handling decision {msg}: {e}")

    def _maybe_execute(self, decision_msg: Dict[str, Any]) -> None:
        now = time.time()
        if self._last_order_ts is not None and (now - self._last_order_ts) < TRADE_INTERVAL_SECONDS:
            # 限频：忽略本次决策
            return

        parsed = self._parse_decision(decision_msg)
        if parsed is None:
            return

        side = parsed["side"]  # 'BUY' or 'SELL'
        quantity = parsed["quantity"]
        price = parsed.get("price")
        pair = parsed.get("pair", self.default_pair)

        # 下单（市价为主，若解析到价格则下限价单）
        if price is None:
            resp = self.client.place_order(pair=pair, side=side, quantity=quantity)
        else:
            resp = self.client.place_order(pair=pair, side=side, quantity=quantity, price=price)

        print(f"[Executor] Placed order: {resp}")
        self._last_order_ts = now

    def _parse_decision(self, decision_msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        极简解析：从 decision 字符串里识别 buy/sell、数量、可选价格与交易对。
        示例：
        - "buy 0.01 BTC" → 市价买 0.01（默认对 BTC/USD）
        - "sell 2 ETH at 3500" → 限价卖 2 at 3500（默认对 ETH/USD）
        - 若无法解析，返回 None
        """
        text = str(decision_msg.get("decision", "")).lower()
        if not text:
            return None

        # 方向
        side = None
        if "buy" in text:
            side = "BUY"
        elif "sell" in text:
            side = "SELL"
        if side is None:
            return None

        # 数量（浮点）
        qty_match = re.search(r"(\d+\.?\d*)", text)
        quantity = float(qty_match.group(1)) if qty_match else 0.01

        # 价格（可选）
        price_match = re.search(r"at\s+(\d+\.?\d*)", text)
        price = float(price_match.group(1)) if price_match else None

        # 交易对（简单从 BTC/ETH/… 推断，默认配 USD）
        pair = self.default_pair
        sym_match = None
        for sym in ["btc", "eth", "sol", "bnb", "doge"]:
            if sym in text:
                sym_match = sym.upper()
                break
        if sym_match is not None:
            pair = f"{sym_match}/USD"

        return {"side": side, "quantity": quantity, "price": price, "pair": pair}

