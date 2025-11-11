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
        self._first_decision_processed = False  # 标记是否已处理第一个决策

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

        # 首先检查是否是wait/hold决策（这是有效的决策，不需要执行交易）
        decision_text = str(decision_msg.get("decision", "")).strip()
        is_wait_hold = False
        action_from_json = None
        
        # 调试：打印完整决策文本（前500字符）
        agent = decision_msg.get("agent", "unknown")
        print(f"[Executor] Debug: 收到决策 (Agent: {agent})")
        print(f"[Executor] Debug: 决策文本前500字符: {decision_text[:500]}")
        
        if decision_text:
            try:
                # 尝试解析JSON格式
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', decision_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    print(f"[Executor] Debug: 提取的JSON: {json_str[:200]}")
                    data = json.loads(json_str)
                    action_from_json = data.get("action", "").lower()
                    print(f"[Executor] Debug: 解析的action: {action_from_json}")
                    
                    # 明确检查：只有wait/hold才是wait/hold，其他action（如open_long, close_long等）都不是
                    if action_from_json in ["wait", "hold"]:
                        is_wait_hold = True
                        print(f"[Executor] Debug: 确认为wait/hold决策")
                    else:
                        print(f"[Executor] Debug: action={action_from_json}，不是wait/hold，继续正常解析")
            except (json.JSONDecodeError, ValueError) as e:
                # JSON解析失败，继续检查自然语言
                print(f"[Executor] Debug: JSON解析失败: {e}")
                pass
            
            # 检查自然语言格式（只有在JSON解析失败或没有action字段时才检查）
            if not is_wait_hold and action_from_json is None:
                text_lower = decision_text.lower()
                # 更严格的检查：确保文本中明确包含wait/hold，且不包含交易动作
                wait_hold_keywords = ["hold", "wait", "no action", "no trade", "do nothing"]
                trade_keywords = ["open_long", "close_long", "buy", "sell", "open", "close"]
                
                has_wait_hold = any(word in text_lower for word in wait_hold_keywords)
                has_trade_action = any(word in text_lower for word in trade_keywords)
                
                # 只有在明确有wait/hold且没有交易动作时才认为是wait/hold
                if has_wait_hold and not has_trade_action:
                    is_wait_hold = True
                    print(f"[Executor] Debug: 自然语言确认为wait/hold")
                elif has_trade_action:
                    print(f"[Executor] Debug: 检测到交易动作，不是wait/hold")
        
        # 如果是第一个决策且是wait/hold，这是合理的保守选择，直接接受
        if is_wait_hold and not self._first_decision_processed:
            agent = decision_msg.get("agent", "unknown")
            print(f"[Executor] ✓ 第一个决策是 wait/hold，这是合理的保守选择 (Agent: {agent})")
            self._first_decision_processed = True
            return
        elif is_wait_hold:
            # 非第一个决策的wait/hold，正常处理
            agent = decision_msg.get("agent", "unknown")
            print(f"[Executor] ✓ 决策为 wait/hold，无需执行交易 (Agent: {agent})")
            return
        else:
            # 不是wait/hold，正常解析
            parsed = self._parse_decision(decision_msg)
        
        # 标记第一个决策已处理（无论是否成功解析）
        if not self._first_decision_processed:
            self._first_decision_processed = True
        
        if parsed is None:
            decision_text = str(decision_msg.get("decision", ""))[:100]
            json_valid = decision_msg.get("json_valid", None)
            
            if json_valid is False:
                print(f"[Executor] ✗ CRITICAL: Decision is not in required JSON format!")
                print(f"    Agent: {decision_msg.get('agent', 'Unknown')}")
                print(f"    Decision: {decision_text}...")
                print(f"    Action: REJECTED - JSON format is mandatory")
                return
            else:
                print(f"[Executor] ✗ 决策无法解析（格式错误）")
                print(f"    Agent: {decision_msg.get('agent', 'Unknown')}")
                print(f"    Decision: {decision_text}...")
                return

        side = parsed["side"]  # 'BUY' or 'SELL'
        quantity = parsed["quantity"]
        price = parsed.get("price")
        pair = parsed.get("pair")
        
        # 如果pair为空或无效，拒绝执行（保守处理，不使用default_pair）
        if not pair:
            print(f"[Executor] ✗ 决策中缺少交易对信息，拒绝执行（保守处理）")
            print(f"    Agent: {decision_msg.get('agent', 'Unknown')}")
            print(f"    注意: 系统不会自动使用默认交易对，请确保决策中包含有效的symbol字段")
            return
        
        # 验证和调整仓位大小（如果有信心度信息）
        if "json_data" in parsed:
            json_data = parsed.get("json_data", {})
            confidence = json_data.get("confidence")
            
            # 计算交易金额
            if price:
                trade_amount = quantity * price
            else:
                # 尝试从market_snapshot获取价格
                market_snapshot = decision_msg.get("market_snapshot")
                if market_snapshot and market_snapshot.get("ticker"):
                    current_price = market_snapshot["ticker"].get("price")
                    if current_price:
                        trade_amount = quantity * current_price
                    else:
                        trade_amount = None
                else:
                    trade_amount = None
            
            # 如果有交易金额和信心度，进行仓位验证和调整
            if trade_amount and confidence:
                adjusted_trade_amount = self._validate_and_adjust_position_size(
                    trade_amount=trade_amount,
                    confidence=confidence,
                    allocated_capital=decision_msg.get("allocated_capital")
                )
                if adjusted_trade_amount != trade_amount:
                    print(f"[Executor] ⚠️ 仓位大小已调整: {trade_amount:.2f} → {adjusted_trade_amount:.2f} USD")
                    # 重新计算quantity
                    if price:
                        quantity = adjusted_trade_amount / price
                    elif market_snapshot and market_snapshot.get("ticker"):
                        current_price = market_snapshot["ticker"].get("price")
                        if current_price:
                            quantity = adjusted_trade_amount / current_price
        
        # 记录解析结果
        order_type = "LIMIT" if price else "MARKET"
        agent = decision_msg.get("agent", "unknown")
        print(f"[Executor] ========================================")
        print(f"[Executor] 决策解析成功")
        print(f"[Executor] ========================================")
        print(f"[Executor] Agent: {agent}")
        print(f"[Executor] 方向: {side}")
        print(f"[Executor] 交易对: {pair}")
        print(f"[Executor] 数量: {quantity}")
        print(f"[Executor] 价格: {price if price else 'MARKET'}")
        print(f"[Executor] 订单类型: {order_type}")
        if "json_data" in parsed:
            print(f"[Executor] 来源: JSON格式")
            json_data = parsed.get("json_data", {})
            if "confidence" in json_data:
                print(f"[Executor] 信心度: {json_data['confidence']}%")
            if "reasoning" in json_data:
                print(f"[Executor] 理由: {json_data['reasoning'][:100]}...")
        else:
            print(f"[Executor] 来源: 自然语言格式")
        print(f"[Executor] ========================================")

        # 下单（市价为主，若解析到价格则下限价单）
        try:
            # 验证参数
            if quantity <= 0:
                print(f"[Executor] ✗ 无效的数量: {quantity}")
                return
            
            if not pair:
                print(f"[Executor] ✗ 无效的交易对: {pair}")
                return
            
            print(f"[Executor] ========================================")
            print(f"[Executor] 准备下单到Roostoo API")
            print(f"[Executor] ========================================")
            print(f"[Executor] 交易对: {pair}")
            print(f"[Executor] 方向: {side}")
            print(f"[Executor] 数量: {quantity}")
            print(f"[Executor] 订单类型: {'LIMIT' if price else 'MARKET'}")
            if price:
                print(f"[Executor] 限价: {price}")
            print(f"[Executor] ========================================")
            
            if self.dry_run:
                # 测试模式：只打印参数，不真正下单
                print(f"[Executor] [DRY RUN] 模拟下单（不会真正执行）")
                print(f"[Executor] [DRY RUN] ✓ 决策已成功解析并准备执行")
                # 在测试模式下也更新时间戳，避免测试时频繁打印
                self._last_order_ts = now
            else:
                # 真实模式：真正下单
                print(f"[Executor] 正在连接Roostoo API...")
                if not self.client:
                    print(f"[Executor] ✗ 错误: RoostooClient未初始化")
                    return
                
                print(f"[Executor] 调用 place_order API...")
                if price is None:
                    resp = self.client.place_order(pair=pair, side=side, quantity=quantity)
                else:
                    resp = self.client.place_order(pair=pair, side=side, quantity=quantity, price=price)
                
                print(f"[Executor] ========================================")
                print(f"[Executor] ✓ 订单已成功提交到Roostoo API")
                print(f"[Executor] ========================================")
                print(f"[Executor] API响应: {resp}")
                print(f"[Executor] ========================================")
                
                # 检查响应是否成功
                if isinstance(resp, dict):
                    if "code" in resp:
                        if resp["code"] == 0 or resp["code"] == 200:
                            print(f"[Executor] ✓ 订单执行成功 (code: {resp['code']})")
                        else:
                            print(f"[Executor] ⚠️ 订单响应代码: {resp['code']}, 消息: {resp.get('message', 'N/A')}")
                    elif "order_id" in resp or "data" in resp:
                        print(f"[Executor] ✓ 订单已创建，响应包含订单信息")
                    else:
                        print(f"[Executor] ⚠️ 订单响应格式异常，但已发送到API")
                
                self._last_order_ts = now
        except Exception as e:
            print(f"[Executor] ========================================")
            print(f"[Executor] ✗ 下单失败")
            print(f"[Executor] ========================================")
            print(f"[Executor] 错误类型: {type(e).__name__}")
            print(f"[Executor] 错误信息: {str(e)}")
            import traceback
            print(f"[Executor] 错误堆栈:")
            traceback.print_exc()
            print(f"[Executor] ========================================")
            if not self.dry_run:
                # 真实模式下记录错误但不中断运行
                print(f"[Executor] ⚠️ 下单失败，但系统继续运行")

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
            # 如果没有symbol，说明决策不完整，返回None（保守处理）
            if not symbol:
                print(f"[Executor] ⚠️ 决策中缺少symbol字段，无法确定交易对，拒绝执行（保守处理）")
                return None
            pair = self._convert_symbol_to_pair(symbol)
            # 如果转换失败（返回None），说明symbol格式有问题
            if not pair:
                print(f"[Executor] ⚠️ 无法从symbol '{symbol}' 确定交易对，拒绝执行（保守处理）")
                return None
            
            # 优先使用quantity字段，如果没有则从position_size_usd计算
            quantity = data.get("quantity")
            if quantity is None:
                # 从position_size_usd计算quantity（需要价格）
                position_size_usd = data.get("position_size_usd")
                price_ref = data.get("price_ref")
                
                if position_size_usd and price_ref:
                    quantity = float(position_size_usd) / float(price_ref)
                else:
                    # 如果都没有，使用默认值
                    quantity = 0.01
            else:
                quantity = float(quantity)
            
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
        
        # 交易对识别（如果无法识别，返回None，不使用default_pair）
        pair = None
        for sym in ["btc", "eth", "sol", "bnb", "doge", "ada", "dot", "link", "matic", "avax", "xrp", "ltc", "bch", "xlm", "atom", "algo", "near", "ftm", "sushi", "uni"]:
            if re.search(rf'\b{sym}\b', text_lower):
                pair = f"{sym.upper()}/USD"
                break
        
        # 如果无法识别交易对，返回None（保守处理，不使用default_pair）
        if not pair:
            print(f"[Executor] ⚠️ 自然语言决策中无法识别交易对，拒绝执行（保守处理）")
            return None
        
        return {"side": side, "quantity": quantity, "price": price, "pair": pair}
    
    def _convert_symbol_to_pair(self, symbol: str) -> Optional[str]:
        """
        转换symbol格式：BTCUSDT -> BTC/USD, BTC/USDT -> BTC/USD
        
        Returns:
            转换后的交易对，如果无法转换则返回None（不使用default_pair，更保守）
        """
        if not symbol:
            return None
        
        # 移除USDT/USD后缀
        base_symbol = symbol.replace("USDT", "").replace("USD", "").replace("/", "").strip()
        
        # 如果移除后缀后为空，说明格式有问题
        if not base_symbol:
            return None
        
        # 添加/USD后缀
        return f"{base_symbol}/USD"
    
    def _validate_and_adjust_position_size(
        self,
        trade_amount: float,
        confidence: Optional[int] = None,
        allocated_capital: Optional[float] = None,
        risk_level: str = "moderate"
    ) -> float:
        """
        验证和调整仓位大小，根据风险等级、信心度和可用资金
        
        Args:
            trade_amount: 原始交易金额（USD）
            confidence: 信心度（0-100）
            allocated_capital: 分配的资金额度（如果提供）
            risk_level: 风险等级（conservative/moderate/aggressive）
            
        Returns:
            调整后的交易金额（USD）
        """
        from config.config import (
            BASE_POSITION_SIZE_RATIO_MODERATE,
            MAX_POSITION_SIZE_RATIO_MODERATE,
            MIN_POSITION_SIZE_USD,
            ABSOLUTE_MAX_POSITION_SIZE_RATIO,
            ABSOLUTE_MAX_POSITION_SIZE_USD,
            CONFIDENCE_THRESHOLD_MODERATE,
            CONFIDENCE_POSITION_MULTIPLIER_MODERATE
        )
        
        # 如果没有分配资金，使用默认值
        if allocated_capital is None or allocated_capital <= 0:
            # 使用默认的moderate参数
            base_ratio = BASE_POSITION_SIZE_RATIO_MODERATE
            max_ratio = MAX_POSITION_SIZE_RATIO_MODERATE
            confidence_threshold = CONFIDENCE_THRESHOLD_MODERATE
            confidence_multiplier = CONFIDENCE_POSITION_MULTIPLIER_MODERATE
            available_capital = 10000.0  # 默认假设
        else:
            # 使用分配的资金
            from config.config import (
                BASE_POSITION_SIZE_RATIO_CONSERVATIVE,
                BASE_POSITION_SIZE_RATIO_AGGRESSIVE,
                MAX_POSITION_SIZE_RATIO_CONSERVATIVE,
                MAX_POSITION_SIZE_RATIO_AGGRESSIVE,
                CONFIDENCE_THRESHOLD_CONSERVATIVE,
                CONFIDENCE_THRESHOLD_AGGRESSIVE,
                CONFIDENCE_POSITION_MULTIPLIER_CONSERVATIVE,
                CONFIDENCE_POSITION_MULTIPLIER_AGGRESSIVE,
                ABSOLUTE_MAX_POSITION_SIZE_RATIO,
                ABSOLUTE_MAX_POSITION_SIZE_USD
            )
            
            if risk_level == "conservative":
                base_ratio = BASE_POSITION_SIZE_RATIO_CONSERVATIVE
                max_ratio = MAX_POSITION_SIZE_RATIO_CONSERVATIVE
                confidence_threshold = CONFIDENCE_THRESHOLD_CONSERVATIVE
                confidence_multiplier = CONFIDENCE_POSITION_MULTIPLIER_CONSERVATIVE
            elif risk_level == "aggressive":
                base_ratio = BASE_POSITION_SIZE_RATIO_AGGRESSIVE
                max_ratio = MAX_POSITION_SIZE_RATIO_AGGRESSIVE
                confidence_threshold = CONFIDENCE_THRESHOLD_AGGRESSIVE
                confidence_multiplier = CONFIDENCE_POSITION_MULTIPLIER_AGGRESSIVE
            else:  # moderate
                base_ratio = BASE_POSITION_SIZE_RATIO_MODERATE
                max_ratio = MAX_POSITION_SIZE_RATIO_MODERATE
                confidence_threshold = CONFIDENCE_THRESHOLD_MODERATE
                confidence_multiplier = CONFIDENCE_POSITION_MULTIPLIER_MODERATE
            
            available_capital = allocated_capital
        
        # 计算基础仓位和最大仓位
        base_position = available_capital * base_ratio
        max_position = available_capital * max_ratio
        
        # 根据信心度调整仓位
        if confidence is not None and confidence > 0:
            # 计算信心度调整系数
            confidence_diff = confidence - confidence_threshold
            confidence_adjustment = 1.0 + (confidence_diff / 100.0) * confidence_multiplier
            # 限制调整范围在0.5到1.5之间
            confidence_adjustment = max(0.5, min(1.5, confidence_adjustment))
            adjusted_base = base_position * confidence_adjustment
        else:
            adjusted_base = base_position
        
        # 确定目标仓位（在基础仓位和最大仓位之间）
        target_position = min(max(adjusted_base, base_position), max_position)
        
        # 调整交易金额
        adjusted_amount = min(trade_amount, target_position)
        
        # 应用绝对上限（无论信心度多高，都不超过此限制）
        absolute_max_by_ratio = available_capital * ABSOLUTE_MAX_POSITION_SIZE_RATIO
        absolute_max = min(absolute_max_by_ratio, ABSOLUTE_MAX_POSITION_SIZE_USD)
        adjusted_amount = min(adjusted_amount, absolute_max)
        
        # 确保不低于最小仓位
        adjusted_amount = max(adjusted_amount, MIN_POSITION_SIZE_USD)
        
        # 确保不超过可用资金（如果有分配资金）
        if allocated_capital and allocated_capital > 0:
            adjusted_amount = min(adjusted_amount, allocated_capital * 0.95)  # 保留5%缓冲
        
        return adjusted_amount

