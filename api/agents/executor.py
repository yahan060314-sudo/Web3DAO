import threading
import time
import re
import json
from typing import Optional, Dict, Any

from api.roostoo_client import RoostooClient
from .bus import MessageBus
from config.config import TRADE_INTERVAL_SECONDS


class TradeExecutor(threading.Thread):
    """
    订阅决策通道，将决策（JSON或自然语言）转为实际下单动作。
    - 遵守 1/min 的限频（使用 TRADE_INTERVAL_SECONDS = 61）
    - 优先解析JSON格式（支持natural_language_prompt.txt的要求）
    - 回退到自然语言解析（兼容旧格式）
    - 改进的自然语言解析（处理模糊表达）
    """

    def __init__(self, bus: MessageBus, decision_topic: str, default_pair: str = "BTC/USD", dry_run: bool = False):
        """
        初始化交易执行器
        
        Args:
            bus: 消息总线
            decision_topic: 决策topic名称
            default_pair: 默认交易对
            dry_run: 如果为True，只打印下单参数，不真正下单（用于测试）
        """
        super().__init__(name="TradeExecutor")
        self.daemon = True
        self.bus = bus
        self.decision_sub = bus.subscribe(decision_topic)
        self.dry_run = dry_run
        if not dry_run:
            self.client = RoostooClient()
            print(f"[Executor] ✓ 真实交易模式已启用 - 将真正执行下单操作")
        else:
            self.client = None
            print(f"[Executor] ⚠️ 测试模式（dry_run=True）- 不会真正下单")
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
            elapsed = now - self._last_order_ts
            print(f"[Executor] Rate limit: {elapsed:.1f}s < {TRADE_INTERVAL_SECONDS}s, skipping order")
            return

        parsed = self._parse_decision(decision_msg)
        if parsed is None:
            decision_text = str(decision_msg.get("decision", ""))[:100]
            json_valid = decision_msg.get("json_valid", None)
            
            if json_valid is False:
                print(f"[Executor] ✗ CRITICAL: Decision is not in required JSON format!")
                print(f"    Agent: {decision_msg.get('agent', 'Unknown')}")
                print(f"    Decision: {decision_text}...")
                print(f"    Action: REJECTED - JSON format is mandatory")
                # 这里可以添加回退逻辑（如使用其他Agent的决策）
                # 但根据用户要求，AI分工还没实现，暂时不添加
                return
            else:
                print(f"[Executor] Failed to parse decision: {decision_text}...")
                print(f"    Note: Decision may be 'wait' or 'hold' (no action needed)")
                return

        side = parsed["side"]  # 'BUY' or 'SELL'
        quantity = parsed["quantity"]
        price = parsed.get("price")
        pair = parsed.get("pair", self.default_pair)
        
        # 记录解析结果
        order_type = "LIMIT" if price else "MARKET"
        print(f"[Executor] Parsed decision:")
        print(f"  Side: {side}")
        print(f"  Pair: {pair}")
        print(f"  Quantity: {quantity}")
        print(f"  Price: {price if price else 'MARKET'}")
        print(f"  Order Type: {order_type}")
        if "json_data" in parsed:
            print(f"  Source: JSON format")
        else:
            print(f"  Source: Natural language format")

        # 下单（市价为主，若解析到价格则下限价单）
        try:
            if self.dry_run:
                # 测试模式：只打印参数，不真正下单
                print(f"[Executor] [DRY RUN] Would place order:")
                print(f"  - pair: {pair}")
                print(f"  - side: {side}")
                print(f"  - quantity: {quantity}")
                print(f"  - price: {price if price else 'MARKET'}")
                print(f"[Executor] [DRY RUN] Order NOT placed (dry_run=True)")
                # 在测试模式下也更新时间戳，避免测试时频繁打印
                self._last_order_ts = now
            else:
                # 真实模式：真正下单
                if price is None:
                    resp = self.client.place_order(pair=pair, side=side, quantity=quantity)
                else:
                    resp = self.client.place_order(pair=pair, side=side, quantity=quantity, price=price)
                
                print(f"[Executor] ✓ Order placed successfully: {resp}")
                self._last_order_ts = now
        except Exception as e:
            print(f"[Executor] ✗ Failed to place order: {e}")
            if not self.dry_run:
                raise  # 真实模式下抛出异常

    def _parse_decision(self, decision_msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析决策：优先JSON格式，回退到自然语言解析。
        
        JSON格式（natural_language_prompt.txt要求）:
        {
          "action": "open_long | close_long | wait | hold",
          "symbol": "BTCUSDT",
          "position_size_usd": 1200.0,
          "price_ref": 100000.0,
          ...
        }
        
        自然语言格式:
        - "buy 0.01 BTC" → 市价买 0.01
        - "sell 2 ETH at 3500" → 限价卖 2 at 3500
        
        若无法解析，返回 None
        """
        decision_text = str(decision_msg.get("decision", "")).strip()
        if not decision_text:
            return None
        
        # 方法1: 尝试解析JSON格式（优先）
        json_parsed = self._parse_json_decision(decision_text)
        if json_parsed:
            return json_parsed
        
        # 方法2: 回退到自然语言解析
        return self._parse_natural_language_decision(decision_text)
    
    def _parse_json_decision(self, text: str) -> Optional[Dict[str, Any]]:
        """
        解析JSON格式决策（natural_language_prompt.txt要求的格式）
        """
        try:
            # 尝试提取JSON（可能被其他文本包围）
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
            else:
                # 尝试直接解析整个文本
                data = json.loads(text.strip())
            
            # 检查action字段
            action = data.get("action", "").lower()
            if action in ["wait", "hold"]:
                # 不执行交易
                return None
            
            # 映射action到side
            side = None
            if action in ["open_long", "buy"]:
                side = "BUY"
            elif action in ["close_long", "sell"]:
                side = "SELL"
            
            if side is None:
                return None
            
            # 提取交易参数
            symbol = data.get("symbol", "").upper()
            # 转换symbol格式：BTCUSDT -> BTC/USD
            pair = self._convert_symbol_to_pair(symbol) if symbol else self.default_pair
            
            # 从position_size_usd计算quantity（需要价格）
            position_size_usd = data.get("position_size_usd")
            price_ref = data.get("price_ref")
            
            if position_size_usd and price_ref:
                quantity = float(position_size_usd) / float(price_ref)
            else:
                # 如果没有position_size_usd，尝试其他字段
                quantity = data.get("quantity", 0.01)
            
            # 提取价格（限价单）
            price = data.get("price") or data.get("price_ref")
            if price:
                price = float(price)
            else:
                price = None
            
            return {
                "side": side,
                "quantity": float(quantity),
                "price": price,
                "pair": pair,
                "json_data": data  # 保留原始JSON数据用于日志
            }
        except (json.JSONDecodeError, ValueError, KeyError, TypeError):
            return None
    
    def _parse_natural_language_decision(self, text: str) -> Optional[Dict[str, Any]]:
        """
        解析自然语言决策（改进版，处理模糊表达）
        """
        text_lower = text.lower()
        
        # 检查是否是hold/wait
        if any(word in text_lower for word in ["hold", "wait", "no action", "no trade"]):
            return None
        
        # 改进的方向识别：查找明确的动作词
        # 避免"I was asked to choose between buy or sell"这种模糊表达
        side = None
        
        # 查找明确的动作模式
        buy_patterns = [
            r'\bbuy\s+(\d+\.?\d*)',  # "buy 0.01"
            r'\bpurchase\s+(\d+\.?\d*)',  # "purchase 0.01"
            r'\bopen\s+long',  # "open long"
            r'\bgoing\s+long',  # "going long"
            r'\bdecide\s+to\s+buy',  # "decide to buy"
            r'\brecommend\s+buying',  # "recommend buying"
        ]
        
        sell_patterns = [
            r'\bsell\s+(\d+\.?\d*)',  # "sell 0.01"
            r'\bclose\s+long',  # "close long"
            r'\bgoing\s+short',  # "going short" (虽然不允许，但识别)
            r'\bdecide\s+to\s+sell',  # "decide to sell"
            r'\brecommend\s+selling',  # "recommend selling"
        ]
        
        # 检查buy模式（优先检查明确的动作）
        for pattern in buy_patterns:
            if re.search(pattern, text_lower):
                side = "BUY"
                break
        
        # 如果没找到buy，检查sell模式
        if side is None:
            for pattern in sell_patterns:
                if re.search(pattern, text_lower):
                    side = "SELL"
                    break
        
        # 如果还是没找到，使用简单的关键词匹配（但更严格）
        if side is None:
            # 只匹配独立的单词，避免匹配"buying"中的"buy"
            if re.search(r'\bbuy\b', text_lower) and not re.search(r'\bsell\b', text_lower):
                side = "BUY"
            elif re.search(r'\bsell\b', text_lower) and not re.search(r'\bbuy\b', text_lower):
                side = "SELL"
            elif re.search(r'\bbuy\b', text_lower) and re.search(r'\bsell\b', text_lower):
                # 同时出现buy和sell，需要更明确的上下文
                # 查找"decide to"或"recommend"等明确动作词
                if re.search(r'(decide|recommend|will|should)\s+.*?\bbuy\b', text_lower):
                    side = "BUY"
                elif re.search(r'(decide|recommend|will|should)\s+.*?\bsell\b', text_lower):
                    side = "SELL"
        
        if side is None:
            return None
        
        # 改进的数量提取：查找紧跟在动作词后的数字
        quantity = 0.01  # 默认值
        qty_patterns = [
            r'\b(?:buy|sell|purchase)\s+(\d+\.?\d*)',  # "buy 0.01"
            r'\b(\d+\.?\d*)\s+(?:btc|eth|sol|bnb|doge)',  # "0.01 BTC"
            r'quantity[:\s]+(\d+\.?\d*)',  # "quantity: 0.01"
            r'amount[:\s]+(\d+\.?\d*)',  # "amount: 0.01"
        ]
        
        for pattern in qty_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    quantity = float(match.group(1))
                    break
                except ValueError:
                    continue
        
        # 价格提取（限价单）
        price = None
        price_patterns = [
            r'\bat\s+(\d+\.?\d*)',  # "at 3500"
            r'price[:\s]+(\d+\.?\d*)',  # "price: 3500"
            r'limit[:\s]+(\d+\.?\d*)',  # "limit: 3500"
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    price = float(match.group(1))
                    break
                except ValueError:
                    continue
        
        # 交易对识别
        pair = self.default_pair
        for sym in ["btc", "eth", "sol", "bnb", "doge"]:
            if re.search(rf'\b{sym}\b', text_lower):
                pair = f"{sym.upper()}/USD"
                break
        
        return {"side": side, "quantity": quantity, "price": price, "pair": pair}
    
    def _convert_symbol_to_pair(self, symbol: str) -> str:
        """
        转换symbol格式：BTCUSDT -> BTC/USD, BTC/USDT -> BTC/USD
        """
        # 移除USDT/USD后缀
        symbol = symbol.replace("USDT", "").replace("USD", "").replace("/", "")
        
        # 添加/USD后缀
        if symbol:
            return f"{symbol}/USD"
        return self.default_pair

