"""
持仓跟踪器 (PositionTracker)
负责跟踪每个Agent的持仓和交易历史

功能：
1. 记录每个Agent的交易历史（买入/卖出）
2. 计算每个Agent的持仓（各币种数量）
3. 计算每个Agent的可用资金（USD）
4. 提供持仓查询接口
"""
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import defaultdict


class PositionTracker:
    """
    持仓跟踪器：跟踪每个Agent的持仓和交易历史
    """
    
    def __init__(self):
        """
        初始化持仓跟踪器
        """
        self.lock = threading.Lock()
        
        # Agent持仓：agent_name -> {currency: quantity}
        # 例如：{"agent_1": {"BTC": 0.005, "ETH": 2.0}, "agent_2": {"BTC": 0.01}}
        self.positions: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        
        # Agent可用资金：agent_name -> usd_balance
        # 例如：{"agent_1": 24500.0, "agent_2": 25000.0}
        self.usd_balances: Dict[str, float] = {}
        
        # Agent初始资金（用于计算）
        self.initial_capital: Dict[str, float] = {}
        
        # 交易历史：agent_name -> List[交易记录]
        # 每条记录：{"timestamp": ..., "type": "BUY"/"SELL", "pair": "BTC/USD", "quantity": 0.005, "price": 100000, "usd_amount": 500}
        self.trade_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    def initialize_agent(self, agent_name: str, initial_capital_usd: float, initial_positions: Optional[Dict[str, float]] = None):
        """
        初始化Agent的账户
        
        Args:
            agent_name: Agent名称
            initial_capital_usd: 初始资金（USD）
            initial_positions: 初始加密货币持仓（可选），例如 {"BTC": 0.0149}
        """
        with self.lock:
            self.initial_capital[agent_name] = initial_capital_usd
            self.usd_balances[agent_name] = initial_capital_usd
            # 初始化持仓
            if agent_name not in self.positions:
                self.positions[agent_name] = defaultdict(float)
            # 如果有初始加密货币持仓，设置它们
            if initial_positions:
                for currency, quantity in initial_positions.items():
                    if quantity > 0:
                        self.positions[agent_name][currency.upper()] = quantity
                positions_str = ", ".join([f"{k}: {v:.8f}" for k, v in initial_positions.items() if v > 0])
                print(f"[PositionTracker] 初始化 {agent_name}: 初始资金 ${initial_capital_usd:.2f} USD, 初始持仓: {positions_str}")
            else:
                print(f"[PositionTracker] 初始化 {agent_name}: 初始资金 ${initial_capital_usd:.2f} USD")
    
    def record_trade(self, 
                    agent_name: str, 
                    side: str, 
                    pair: str, 
                    quantity: float, 
                    price: Optional[float] = None,
                    usd_amount: Optional[float] = None,
                    order_id: Optional[str] = None) -> bool:
        """
        记录交易并更新持仓
        
        Args:
            agent_name: Agent名称
            side: 交易方向 ("BUY" 或 "SELL")
            pair: 交易对 (如 "BTC/USD")
            quantity: 交易数量
            price: 交易价格（可选，用于计算USD金额）
            usd_amount: 交易金额（USD，如果提供则优先使用）
            order_id: 订单ID（可选）
            
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                # 解析交易对，提取币种
                # "BTC/USD" -> base="BTC", quote="USD"
                if "/" in pair:
                    base, quote = pair.split("/", 1)
                else:
                    # 如果没有斜杠，尝试从pair中提取（如"BTCUSDT"）
                    base = pair.replace("USDT", "").replace("USD", "")
                    quote = "USD"
                
                base = base.strip().upper()
                quote = quote.strip().upper()
                
                # 计算USD金额
                if usd_amount is None:
                    if price is not None:
                        usd_amount = quantity * price
                    else:
                        # 如果没有价格，无法计算，使用0
                        usd_amount = 0.0
                        print(f"[PositionTracker] ⚠️ 无法计算USD金额（缺少价格）: {agent_name}, {side}, {pair}, {quantity}")
                
                # 更新持仓
                if side.upper() == "BUY":
                    # 买入：增加币种持仓，减少USD
                    self.positions[agent_name][base] += quantity
                    self.usd_balances[agent_name] = self.usd_balances.get(agent_name, 0.0) - usd_amount
                elif side.upper() == "SELL":
                    # 卖出：减少币种持仓，增加USD
                    current_position = self.positions[agent_name].get(base, 0.0)
                    if current_position < quantity:
                        print(f"[PositionTracker] ⚠️ {agent_name} 尝试卖出 {quantity} {base}，但只持有 {current_position}")
                        # 允许部分卖出（卖出所有持仓）
                        quantity = current_position
                    
                    if quantity > 0:
                        self.positions[agent_name][base] -= quantity
                        self.usd_balances[agent_name] = self.usd_balances.get(agent_name, 0.0) + usd_amount
                else:
                    print(f"[PositionTracker] ⚠️ 未知的交易方向: {side}")
                    return False
                
                # 清理零持仓
                if self.positions[agent_name][base] < 0.00000001:  # 小于最小精度
                    self.positions[agent_name][base] = 0.0
                
                # 记录交易历史
                trade_record = {
                    "timestamp": datetime.now().isoformat(),
                    "type": side.upper(),
                    "pair": pair,
                    "base": base,
                    "quote": quote,
                    "quantity": quantity,
                    "price": price,
                    "usd_amount": usd_amount,
                    "order_id": order_id
                }
                self.trade_history[agent_name].append(trade_record)
                
                # 打印更新信息
                print(f"[PositionTracker] ✓ {agent_name} {side} {quantity} {base} @ ${price if price else 'MARKET'}")
                print(f"   持仓: {base}={self.positions[agent_name][base]:.8f}, USD=${self.usd_balances[agent_name]:.2f}")
                
                return True
                
            except Exception as e:
                print(f"[PositionTracker] ❌ 记录交易失败: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    def get_positions(self, agent_name: str) -> Dict[str, float]:
        """
        获取Agent的持仓
        
        Args:
            agent_name: Agent名称
            
        Returns:
            持仓字典：{currency: quantity}
        """
        with self.lock:
            positions = dict(self.positions[agent_name])
            # 过滤掉零持仓
            return {k: v for k, v in positions.items() if v > 0.00000001}
    
    def get_usd_balance(self, agent_name: str) -> float:
        """
        获取Agent的USD余额
        
        Args:
            agent_name: Agent名称
            
        Returns:
            USD余额
        """
        with self.lock:
            return self.usd_balances.get(agent_name, 0.0)
    
    def get_position(self, agent_name: str, currency: str) -> float:
        """
        获取Agent特定币种的持仓
        
        Args:
            agent_name: Agent名称
            currency: 币种（如 "BTC", "ETH"）
            
        Returns:
            持仓数量
        """
        with self.lock:
            return self.positions[agent_name].get(currency.upper(), 0.0)
    
    def get_trade_history(self, agent_name: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取Agent的交易历史
        
        Args:
            agent_name: Agent名称
            limit: 返回最近N条记录（None表示全部）
            
        Returns:
            交易历史列表
        """
        with self.lock:
            history = self.trade_history[agent_name].copy()
            if limit:
                return history[-limit:]
            return history
    
    def get_total_value_usd(self, agent_name: str, current_prices: Dict[str, float]) -> float:
        """
        计算Agent的总资产价值（USD）
        
        Args:
            agent_name: Agent名称
            current_prices: 当前价格字典 {currency: price}
            
        Returns:
            总资产价值（USD）
        """
        with self.lock:
            total = self.usd_balances.get(agent_name, 0.0)
            positions = self.positions[agent_name]
            
            for currency, quantity in positions.items():
                if quantity > 0.00000001 and currency in current_prices:
                    total += quantity * current_prices[currency]
            
            return total
    
    def get_summary(self, agent_name: str) -> Dict[str, Any]:
        """
        获取Agent的持仓摘要
        
        Args:
            agent_name: Agent名称
            
        Returns:
            持仓摘要字典
        """
        with self.lock:
            positions = self.get_positions(agent_name)
            usd_balance = self.get_usd_balance(agent_name)
            initial = self.initial_capital.get(agent_name, 0.0)
            trade_count = len(self.trade_history[agent_name])
            
            return {
                "agent_name": agent_name,
                "initial_capital": initial,
                "usd_balance": usd_balance,
                "positions": positions,
                "trade_count": trade_count,
                "total_currencies": len(positions)
            }
    
    def format_positions_for_llm(self, agent_name: str, current_prices: Optional[Dict[str, float]] = None) -> str:
        """
        格式化持仓信息为LLM可读的文本
        
        Args:
            agent_name: Agent名称
            current_prices: 当前价格字典（可选，用于计算持仓价值）
            
        Returns:
            格式化的文本
        """
        # 注意：get_positions 和 get_usd_balance 内部已经使用了锁，所以这里不需要再加锁
        # 直接调用即可，它们会自己处理锁
        positions = self.get_positions(agent_name)
        usd_balance = self.get_usd_balance(agent_name)
        
        lines = [f"📊 Your Current Holdings ({agent_name}):"]
        lines.append(f"  💵 USD Balance: ${usd_balance:.2f}")
        
        if positions:
            lines.append(f"  🪙 Cryptocurrency Holdings:")
            total_value = usd_balance
            for currency, quantity in sorted(positions.items()):
                if current_prices and currency in current_prices:
                    price = current_prices[currency]
                    value = quantity * price
                    total_value += value
                    lines.append(f"    {currency}: {quantity:.8f} (Value: ${value:.2f} @ ${price:.2f})")
                else:
                    lines.append(f"    {currency}: {quantity:.8f}")
                    if current_prices:
                        lines.append(f"      (Price not available for {currency})")
            
            if current_prices:
                lines.append(f"  💰 Total Portfolio Value: ${total_value:.2f}")
        else:
            lines.append(f"  🪙 No cryptocurrency holdings")
        
        return "\n".join(lines)
    
    def print_summary(self, agent_name: Optional[str] = None):
        """
        打印持仓摘要
        
        Args:
            agent_name: Agent名称（None表示打印所有Agent）
        """
        with self.lock:
            if agent_name:
                agents = [agent_name]
            else:
                agents = list(set(list(self.positions.keys()) + list(self.usd_balances.keys())))
            
            if not agents:
                print("[PositionTracker] 没有Agent持仓记录")
                return
            
            print("=" * 80)
            print("持仓摘要")
            print("=" * 80)
            
            for agent in agents:
                summary = self.get_summary(agent)
                print(f"\n{agent}:")
                print(f"  初始资金: ${summary['initial_capital']:.2f} USD")
                print(f"  USD余额: ${summary['usd_balance']:.2f} USD")
                print(f"  持仓数量: {summary['total_currencies']} 种币种")
                if summary['positions']:
                    print(f"  持仓详情:")
                    for currency, quantity in summary['positions'].items():
                        print(f"    {currency}: {quantity:.8f}")
                else:
                    print(f"  持仓详情: 无")
                print(f"  交易次数: {summary['trade_count']}")
            
            print("=" * 80)







