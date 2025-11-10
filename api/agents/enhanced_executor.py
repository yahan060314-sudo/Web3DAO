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
                 enable_multi_ai_consensus: bool = True):
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
        """
        super().__init__(name="EnhancedTradeExecutor")
        self.daemon = True
        self.bus = bus
        self.decision_sub = bus.subscribe(decision_topic)
        self.dry_run = dry_run
        self.default_pair = default_pair
        self._stopped = False
        self._last_order_ts: Optional[float] = None
        
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
                self._execute_decision(consensus_decision, decision_id)
                return
        
        # 3. 单AI决策执行
        # 解析决策（使用原有的解析逻辑）
        parsed = self._parse_decision(decision_msg)
        
        if parsed is None:
            # 决策无法解析
            if json_valid is False:
                print(f"[EnhancedExecutor] ✗ 决策格式无效（非JSON）")
            else:
                print(f"[EnhancedExecutor] ⚠️ 决策无法解析（可能是 wait/hold）")
            
            # 记录执行结果（失败）
            if self.decision_manager and decision_id:
                self.decision_manager.record_execution_result(
                    decision_id=decision_id,
                    status="failed",
                    error="Decision cannot be parsed"
                )
            return
        
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
        self._execute_decision(parsed, decision_id, market_snapshot)
    
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
                         market_snapshot: Optional[Dict[str, Any]] = None) -> None:
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
        
        # 记录决策信息
        order_type = "LIMIT" if price else "MARKET"
        print(f"[EnhancedExecutor] 执行决策:")
        print(f"  Side: {side}")
        print(f"  Pair: {pair}")
        print(f"  Quantity: {quantity}")
        print(f"  Price: {price if price else 'MARKET'}")
        print(f"  Order Type: {order_type}")
        
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
                
                self._last_order_ts = now
            else:
                # 真实模式：真正下单
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
                
                self._last_order_ts = now
        except Exception as e:
            execution_time = time.time() - execution_start
            error_msg = str(e)
            print(f"[EnhancedExecutor] ✗ 订单执行失败: {error_msg}")
            
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

