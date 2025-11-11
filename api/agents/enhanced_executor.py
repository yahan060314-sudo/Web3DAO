"""
增强版交易执行器 (Enhanced TradeExecutor)
集成 DecisionManager，支持决策存储、验证、多AI综合等功能
"""
import threading
import time
import re
import json
from typing import Optional, Dict, Any

from api.roostoo_client import RoostooClient
from .bus import MessageBus
from .decision_manager import DecisionManager
from .capital_manager import CapitalManager
from config.config import TRADE_INTERVAL_SECONDS


class EnhancedTradeExecutor(threading.Thread):
    """
    增强版交易执行器：
    - 集成 DecisionManager（决策存储、验证、多AI综合）
    - 支持决策持久化
    - 支持决策验证
    - 支持多AI决策综合
    - 支持执行结果记录
    - 遵守限频规则
    """
    
    def __init__(self, 
                 bus: MessageBus, 
                 decision_topic: str, 
                 default_pair: str = "BTC/USD",
                 dry_run: bool = False,
                 enable_decision_manager: bool = True,
                 db_path: str = "decisions.db",
                 enable_multi_ai_consensus: bool = True,
                 capital_manager: Optional[CapitalManager] = None):
        """
        初始化增强版交易执行器
        
        Args:
            bus: 消息总线
            decision_topic: 决策topic名称
            default_pair: 默认交易对
            dry_run: 如果为True，只打印下单参数，不真正下单
            enable_decision_manager: 是否启用决策管理器
            db_path: 数据库文件路径
            enable_multi_ai_consensus: 是否启用多AI决策综合
            capital_manager: 资本管理器（用于管理资金分配）
        """
        super().__init__(name="EnhancedTradeExecutor")
        self.daemon = True
        self.bus = bus
        self.decision_sub = bus.subscribe(decision_topic)
        self.dry_run = dry_run
        self.default_pair = default_pair
        self._stopped = False
        self._last_order_ts: Optional[float] = None
        
        # 初始化资本管理器
        self.capital_manager = capital_manager
        if capital_manager:
            print(f"[EnhancedExecutor] ✓ 资本管理器已启用")
        
        # 初始化 Roostoo 客户端
        if not dry_run:
            self.client = RoostooClient()
            print(f"[EnhancedExecutor] ✓ 真实交易模式已启用")
        else:
            self.client = None
            print(f"[EnhancedExecutor] ⚠️ 测试模式（dry_run=True）")
        
        # 初始化决策管理器
        self.enable_decision_manager = enable_decision_manager
        if enable_decision_manager:
            self.decision_manager = DecisionManager(
                db_path=db_path,
                enable_multi_ai_consensus=enable_multi_ai_consensus
            )
            print(f"[EnhancedExecutor] ✓ 决策管理器已启用: {db_path}")
        else:
            self.decision_manager = None
        
        # 决策缓存（用于多AI综合）
        self.decision_cache: Dict[str, Dict[str, Any]] = {}  # agent -> latest_decision
        self.consensus_window = 2.0  # 决策综合时间窗口（秒）
    
    def stop(self):
        """停止执行器"""
        self._stopped = True
    
    def run(self):
        """主循环：接收决策并执行"""
        print(f"[EnhancedExecutor] 启动执行器...")
        while not self._stopped:
            msg = self.decision_sub.recv(timeout=0.5)
            if msg is None:
                continue
            
            try:
                self._process_decision(msg)
            except Exception as e:
                print(f"[EnhancedExecutor] ✗ 处理决策失败: {e}")
                import traceback
                traceback.print_exc()
    
    def _process_decision(self, decision_msg: Dict[str, Any]) -> None:
        """
        处理决策消息
        
        Args:
            decision_msg: 决策消息，包含 agent, decision, market_snapshot, timestamp, json_valid
        """
        agent = decision_msg.get("agent", "unknown")
        decision_text = decision_msg.get("decision", "")
        market_snapshot = decision_msg.get("market_snapshot")
        timestamp = decision_msg.get("timestamp", time.time())
        json_valid = decision_msg.get("json_valid", False)
        
        # 1. 存储决策到数据库
        decision_id = None
        if self.decision_manager:
            try:
                decision_id = self.decision_manager.add_decision(decision_msg)
            except Exception as e:
                print(f"[EnhancedExecutor] ⚠️ 存储决策失败: {e}")
        
        # 2. 更新决策缓存（用于多AI综合）
        if self.enable_decision_manager and self.decision_manager.enable_multi_ai_consensus:
            self.decision_cache[agent] = {
                "decision": decision_text,
                "market_snapshot": market_snapshot,
                "timestamp": timestamp,
                "json_valid": json_valid,
                "decision_id": decision_id
            }
            
            # 检查是否有其他AI的决策（在时间窗口内）
            consensus_decision = self._try_get_consensus()
            if consensus_decision:
                print(f"[EnhancedExecutor] ✓ 获取到多AI共识决策")
                consensus_decision["agent"] = agent  # 添加agent信息
                consensus_decision["market_snapshot"] = market_snapshot  # 添加市场快照
                self._execute_decision(consensus_decision, decision_id, market_snapshot, agent)
                return
        
        # 3. 单AI决策执行
        # 首先检查是否是wait/hold决策（这是有效的决策，不需要执行交易）
        decision_text = str(decision_msg.get("decision", "")).strip()
        is_wait_hold = False
        if decision_text:
            try:
                # 尝试解析JSON格式
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', decision_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    data = json.loads(json_str)
                    action = data.get("action", "").lower()
                    if action in ["wait", "hold"]:
                        is_wait_hold = True
            except (json.JSONDecodeError, ValueError):
                pass
            
            # 检查自然语言格式
            if not is_wait_hold:
                text_lower = decision_text.lower()
                if any(word in text_lower for word in ["hold", "wait", "no action", "no trade", "do nothing"]):
                    is_wait_hold = True
        
        if is_wait_hold:
            # wait/hold是有效的决策，不需要执行交易
            print(f"[EnhancedExecutor] ✓ 决策为 wait/hold，无需执行交易")
            
            # 记录执行结果（跳过，不是失败）
            if self.decision_manager and decision_id:
                self.decision_manager.record_execution_result(
                    decision_id=decision_id,
                    status="skipped",
                    error="Decision is wait/hold, no action needed"
                )
            return
        
        # 解析决策（使用原有的解析逻辑）
        parsed = self._parse_decision(decision_msg)
        
        if parsed is None:
            # 决策无法解析（不是wait/hold，但无法解析）
            if json_valid is False:
                print(f"[EnhancedExecutor] ✗ 决策格式无效（非JSON）")
            else:
                print(f"[EnhancedExecutor] ✗ 决策无法解析（格式错误）")
            
            # 记录执行结果（失败）
            if self.decision_manager and decision_id:
                self.decision_manager.record_execution_result(
                    decision_id=decision_id,
                    status="failed",
                    error="Decision cannot be parsed"
                )
            return
        
        # 添加agent信息到parsed决策中
        parsed["agent"] = agent
        parsed["market_snapshot"] = market_snapshot
        
        # 4. 验证决策
        if self.decision_manager:
            current_price = None
            if market_snapshot and market_snapshot.get("ticker"):
                current_price = market_snapshot["ticker"].get("price")
            
            is_valid, error_msg = self.decision_manager.validate_decision(
                parsed,
                current_price=current_price
            )
            
            if not is_valid:
                print(f"[EnhancedExecutor] ✗ 决策验证失败: {error_msg}")
                # 记录执行结果（失败）
                if decision_id:
                    self.decision_manager.record_execution_result(
                        decision_id=decision_id,
                        status="failed",
                        error=error_msg
                    )
                return
        
        # 5. 执行决策
        self._execute_decision(parsed, decision_id, market_snapshot, agent)
    
    def _try_get_consensus(self) -> Optional[Dict[str, Any]]:
        """
        尝试获取多AI共识决策
        
        Returns:
            共识决策，如果无法达成共识则返回None
        """
        if not self.decision_manager or not self.decision_manager.enable_multi_ai_consensus:
            return None
        
        # 收集时间窗口内的决策
        now = time.time()
        recent_decisions = []
        
        for agent, decision_data in self.decision_cache.items():
            age = now - decision_data["timestamp"]
            if age <= self.consensus_window:
                # 尝试解析决策
                parsed = self._parse_decision(decision_data)
                if parsed:
                    recent_decisions.append(parsed)
        
        # 如果只有一个决策，直接返回
        if len(recent_decisions) == 1:
            return recent_decisions[0]
        
        # 如果有多个决策，尝试获取共识
        if len(recent_decisions) > 1:
            consensus = self.decision_manager.get_consensus_decision(recent_decisions)
            return consensus
        
        return None
    
    def _execute_decision(self, 
                         parsed_decision: Dict[str, Any],
                         decision_id: Optional[int] = None,
                         market_snapshot: Optional[Dict[str, Any]] = None,
                         agent_name: Optional[str] = None) -> None:
        """
        执行决策
        
        Args:
            parsed_decision: 解析后的决策（包含 side, quantity, price, pair）
            decision_id: 决策ID（用于记录执行结果）
            market_snapshot: 市场快照（用于验证）
        """
        # 检查限频
        now = time.time()
        if self._last_order_ts is not None and (now - self._last_order_ts) < TRADE_INTERVAL_SECONDS:
            elapsed = now - self._last_order_ts
            print(f"[EnhancedExecutor] ⚠️ 限频保护: {elapsed:.1f}s < {TRADE_INTERVAL_SECONDS}s，跳过本次执行")
            
            # 记录执行结果（限频跳过）
            if self.decision_manager and decision_id:
                self.decision_manager.record_execution_result(
                    decision_id=decision_id,
                    status="skipped",
                    error=f"Rate limit: {elapsed:.1f}s < {TRADE_INTERVAL_SECONDS}s"
                )
            return
        
        side = parsed_decision["side"]
        quantity = parsed_decision["quantity"]
        price = parsed_decision.get("price")
        pair = parsed_decision.get("pair", self.default_pair)
        # 优先使用参数中的agent_name，如果没有则从parsed_decision中获取
        agent_name = agent_name or parsed_decision.get("agent", "unknown")
        
        # 计算交易金额（用于资金检查）
        # 优先使用参数中的market_snapshot，如果没有则从parsed_decision中获取
        snapshot_for_price = market_snapshot or parsed_decision.get("market_snapshot")
        
        if price:
            trade_amount = quantity * price
        else:
            # 如果没有价格，使用市场快照中的价格
            if snapshot_for_price and snapshot_for_price.get("ticker"):
                current_price = snapshot_for_price["ticker"].get("price")
                if current_price:
                    trade_amount = quantity * current_price
                else:
                    trade_amount = None
            else:
                trade_amount = None
        
        # 验证和调整仓位大小（根据风险等级和信心度）
        if trade_amount and self.capital_manager:
            adjusted_trade_amount = self._validate_and_adjust_position_size(
                trade_amount=trade_amount,
                agent_name=agent_name,
                confidence=parsed_decision.get("json_data", {}).get("confidence"),
                risk_level="moderate"  # 默认使用moderate，可以从decision消息中获取
            )
            if adjusted_trade_amount != trade_amount:
                print(f"[EnhancedExecutor] ⚠️ 仓位大小已调整: {trade_amount:.2f} → {adjusted_trade_amount:.2f} USD")
                # 重新计算quantity
                if price:
                    quantity = adjusted_trade_amount / price
                elif snapshot_for_price and snapshot_for_price.get("ticker"):
                    current_price = snapshot_for_price["ticker"].get("price")
                    if current_price:
                        quantity = adjusted_trade_amount / current_price
                trade_amount = adjusted_trade_amount
        
        # 检查资金额度（如果启用了资本管理器）
        if self.capital_manager and trade_amount:
            allocated_capital = self.capital_manager.get_allocated_capital(agent_name)
            available_capital = self.capital_manager.get_available_capital(agent_name)
            
            if allocated_capital > 0:
                # Agent有资金限制
                if trade_amount > available_capital:
                    print(f"[EnhancedExecutor] ✗ {agent_name} 可用资金不足: {available_capital:.2f} USD < {trade_amount:.2f} USD")
                    
                    # 记录执行结果（资金不足）
                    if self.decision_manager and decision_id:
                        self.decision_manager.record_execution_result(
                            decision_id=decision_id,
                            status="failed",
                            error=f"Insufficient capital: {available_capital:.2f} < {trade_amount:.2f}"
                        )
                    return
                
                # 预留资金
                if not self.capital_manager.reserve_capital(agent_name, trade_amount):
                    print(f"[EnhancedExecutor] ✗ {agent_name} 资金预留失败")
                    if self.decision_manager and decision_id:
                        self.decision_manager.record_execution_result(
                            decision_id=decision_id,
                            status="failed",
                            error="Capital reservation failed"
                        )
                    return
        
        # 记录决策信息
        order_type = "LIMIT" if price else "MARKET"
        print(f"[EnhancedExecutor] 执行决策:")
        print(f"  Agent: {agent_name}")
        print(f"  Side: {side}")
        print(f"  Pair: {pair}")
        print(f"  Quantity: {quantity}")
        print(f"  Price: {price if price else 'MARKET'}")
        print(f"  Order Type: {order_type}")
        if trade_amount:
            print(f"  Trade Amount: {trade_amount:.2f} USD")
            if self.capital_manager:
                available = self.capital_manager.get_available_capital(agent_name)
                print(f"  Available Capital: {available:.2f} USD")
        
        # 执行交易
        execution_start = time.time()
        try:
            if self.dry_run:
                # 测试模式：只打印参数
                print(f"[EnhancedExecutor] [DRY RUN] 模拟下单:")
                print(f"  - pair: {pair}")
                print(f"  - side: {side}")
                print(f"  - quantity: {quantity}")
                print(f"  - price: {price if price else 'MARKET'}")
                
                # 模拟执行成功
                execution_time = time.time() - execution_start
                order_id = f"dry_run_{int(time.time())}"
                
                # 记录执行结果
                if self.decision_manager and decision_id:
                    self.decision_manager.record_execution_result(
                        decision_id=decision_id,
                        order_id=order_id,
                        status="success",
                        execution_time=execution_time
                    )
                
                # 在dry_run模式下，不真正占用资金，但可以记录
                # 如果启用了资本管理器，可以在dry_run模式下模拟资金使用
                # 这里我们选择不占用资金，因为dry_run只是测试
                
                self._last_order_ts = now
            else:
                # 真实模式：真正下单
                try:
                    if price is None:
                        resp = self.client.place_order(pair=pair, side=side, quantity=quantity)
                    else:
                        resp = self.client.place_order(pair=pair, side=side, quantity=quantity, price=price)
                    
                    execution_time = time.time() - execution_start
                    order_id = resp.get("order_id") if isinstance(resp, dict) else str(resp)
                    
                    print(f"[EnhancedExecutor] ✓ 订单执行成功: {order_id}")
                    
                    # 记录执行结果
                    if self.decision_manager and decision_id:
                        self.decision_manager.record_execution_result(
                            decision_id=decision_id,
                            order_id=order_id,
                            status="success",
                            execution_time=execution_time
                        )
                    
                    # 注意：在真实交易中，资金已经通过交易所扣除
                    # 这里不需要手动释放资金，因为资金已经在交易所账户中
                    # 但我们可以更新资本管理器的记录（如果需要）
                    
                    self._last_order_ts = now
                except Exception as order_error:
                    # 订单失败，释放预留的资金
                    if self.capital_manager and trade_amount:
                        self.capital_manager.release_capital(agent_name, trade_amount)
                    raise order_error
        except Exception as e:
            execution_time = time.time() - execution_start
            error_msg = str(e)
            print(f"[EnhancedExecutor] ✗ 订单执行失败: {error_msg}")
            
            # 如果订单失败，释放预留的资金
            if self.capital_manager and trade_amount and not self.dry_run:
                self.capital_manager.release_capital(agent_name, trade_amount)
            
            # 记录执行结果（失败）
            if self.decision_manager and decision_id:
                self.decision_manager.record_execution_result(
                    decision_id=decision_id,
                    status="failed",
                    error=error_msg,
                    execution_time=execution_time
                )
            
            if not self.dry_run:
                raise  # 真实模式下抛出异常
    
    def get_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取执行统计信息
        
        Args:
            hours: 统计时间范围（小时）
            
        Returns:
            统计信息字典
        """
        if self.decision_manager:
            return self.decision_manager.get_statistics(hours=hours)
        return {}
    
    def _parse_decision(self, decision_msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析决策：优先JSON格式，回退到自然语言解析。
        （从 TradeExecutor 复制的方法）
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
        """解析JSON格式决策"""
        try:
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
            else:
                data = json.loads(text.strip())
            
            action = data.get("action", "").lower()
            if action in ["wait", "hold"]:
                return None
            
            side = None
            if action in ["open_long", "buy"]:
                side = "BUY"
            elif action in ["close_long", "sell"]:
                side = "SELL"
            
            if side is None:
                return None
            
            symbol = data.get("symbol", "").upper()
            pair = self._convert_symbol_to_pair(symbol) if symbol else self.default_pair
            
            position_size_usd = data.get("position_size_usd")
            price_ref = data.get("price_ref")
            
            if position_size_usd and price_ref:
                quantity = float(position_size_usd) / float(price_ref)
            else:
                quantity = data.get("quantity", 0.01)
            
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
                "json_data": data
            }
        except (json.JSONDecodeError, ValueError, KeyError, TypeError):
            return None
    
    def _parse_natural_language_decision(self, text: str) -> Optional[Dict[str, Any]]:
        """解析自然语言决策"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["hold", "wait", "no action", "no trade"]):
            return None
        
        side = None
        buy_patterns = [
            r'\bbuy\s+(\d+\.?\d*)',
            r'\bpurchase\s+(\d+\.?\d*)',
            r'\bopen\s+long',
            r'\bgoing\s+long',
            r'\bdecide\s+to\s+buy',
            r'\brecommend\s+buying',
        ]
        
        sell_patterns = [
            r'\bsell\s+(\d+\.?\d*)',
            r'\bclose\s+long',
            r'\bdecide\s+to\s+sell',
            r'\brecommend\s+selling',
        ]
        
        for pattern in buy_patterns:
            if re.search(pattern, text_lower):
                side = "BUY"
                break
        
        if side is None:
            for pattern in sell_patterns:
                if re.search(pattern, text_lower):
                    side = "SELL"
                    break
        
        if side is None:
            if re.search(r'\bbuy\b', text_lower) and not re.search(r'\bsell\b', text_lower):
                side = "BUY"
            elif re.search(r'\bsell\b', text_lower) and not re.search(r'\bbuy\b', text_lower):
                side = "SELL"
        
        if side is None:
            return None
        
        quantity = 0.01
        qty_patterns = [
            r'\b(?:buy|sell|purchase)\s+(\d+\.?\d*)',
            r'\b(\d+\.?\d*)\s+(?:btc|eth|sol|bnb|doge)',
            r'quantity[:\s]+(\d+\.?\d*)',
            r'amount[:\s]+(\d+\.?\d*)',
        ]
        
        for pattern in qty_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    quantity = float(match.group(1))
                    break
                except ValueError:
                    continue
        
        price = None
        price_patterns = [
            r'\bat\s+(\d+\.?\d*)',
            r'price[:\s]+(\d+\.?\d*)',
            r'limit[:\s]+(\d+\.?\d*)',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    price = float(match.group(1))
                    break
                except ValueError:
                    continue
        
        pair = self.default_pair
        for sym in ["btc", "eth", "sol", "bnb", "doge"]:
            if re.search(rf'\b{sym}\b', text_lower):
                pair = f"{sym.upper()}/USD"
                break
        
        return {"side": side, "quantity": quantity, "price": price, "pair": pair}
    
    def _convert_symbol_to_pair(self, symbol: str) -> str:
        """转换symbol格式：BTCUSDT -> BTC/USD"""
        symbol = symbol.replace("USDT", "").replace("USD", "").replace("/", "")
        if symbol:
            return f"{symbol}/USD"
        return self.default_pair
    
    def _validate_and_adjust_position_size(
        self,
        trade_amount: float,
        agent_name: str,
        confidence: Optional[int] = None,
        risk_level: str = "moderate"
    ) -> float:
        """
        验证和调整仓位大小，根据风险等级、信心度和可用资金
        
        Args:
            trade_amount: 原始交易金额（USD）
            agent_name: Agent名称
            confidence: 信心度（0-100）
            risk_level: 风险等级（conservative/moderate/aggressive）
            
        Returns:
            调整后的交易金额（USD）
        """
        if not self.capital_manager:
            return trade_amount
        
        from config.config import (
            BASE_POSITION_SIZE_RATIO_CONSERVATIVE,
            BASE_POSITION_SIZE_RATIO_MODERATE,
            BASE_POSITION_SIZE_RATIO_AGGRESSIVE,
            MAX_POSITION_SIZE_RATIO_CONSERVATIVE,
            MAX_POSITION_SIZE_RATIO_MODERATE,
            MAX_POSITION_SIZE_RATIO_AGGRESSIVE,
            MIN_POSITION_SIZE_USD,
            ABSOLUTE_MAX_POSITION_SIZE_RATIO,
            ABSOLUTE_MAX_POSITION_SIZE_USD,
            CONFIDENCE_THRESHOLD_CONSERVATIVE,
            CONFIDENCE_THRESHOLD_MODERATE,
            CONFIDENCE_THRESHOLD_AGGRESSIVE,
            CONFIDENCE_POSITION_MULTIPLIER_CONSERVATIVE,
            CONFIDENCE_POSITION_MULTIPLIER_MODERATE,
            CONFIDENCE_POSITION_MULTIPLIER_AGGRESSIVE
        )
        
        # 获取可用资金
        available_capital = self.capital_manager.get_available_capital(agent_name)
        if available_capital <= 0:
            return min(trade_amount, MIN_POSITION_SIZE_USD)
        
        # 根据风险等级选择参数
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
        
        # 确保不超过可用资金
        adjusted_amount = min(adjusted_amount, available_capital * 0.95)  # 保留5%缓冲
        
        return adjusted_amount


if __name__ == "__main__":
    # 测试代码
    from .bus import MessageBus
    
    bus = MessageBus()
    executor = EnhancedTradeExecutor(
        bus=bus,
        decision_topic="decisions",
        default_pair="BTC/USD",
        dry_run=True,
        enable_decision_manager=True,
        enable_multi_ai_consensus=True
    )
    
    # 启动执行器
    executor.start()
    
    # 模拟决策消息
    test_decision = {
        "agent": "test_agent",
        "decision": '{"action": "buy", "quantity": 0.01, "symbol": "BTCUSDT"}',
        "market_snapshot": {
            "ticker": {"price": 50000.0},
            "balance": {}
        },
        "timestamp": time.time(),
        "json_valid": True
    }
    
    # 发布决策
    bus.publish("decisions", test_decision)
    
    # 等待处理
    time.sleep(2)
    
    # 获取统计信息
    stats = executor.get_statistics()
    print(f"统计信息: {stats}")
    
    # 停止执行器
    executor.stop()

