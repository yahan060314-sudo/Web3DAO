"""
数据格式化模块 - 将Roostoo原始数据转换为Agent友好的结构化格式

这个模块负责：
1. 将Roostoo API返回的原始数据格式化为统一的结构
2. 提取关键市场指标（价格、成交量、涨跌幅等）
3. 格式化账户信息（余额、持仓等）
4. 提供数据摘要功能，方便Agent快速理解市场状态
"""

from typing import Dict, Any, Optional, List
import time


class DataFormatter:
    """
    数据格式化器：将Roostoo API返回的原始数据转换为Agent可理解的结构化格式
    """
    
    @staticmethod
    def format_ticker(raw_ticker: Dict[str, Any], pair: Optional[str] = None) -> Dict[str, Any]:
        """
        格式化Ticker数据（市场行情快照）
        
        Args:
            raw_ticker: Roostoo API返回的原始ticker数据
            pair: 交易对名称（如 "BTC/USD"）
            
        Returns:
            格式化的ticker数据，包含：
            - pair: 交易对
            - price: 当前价格
            - volume_24h: 24小时成交量
            - change_24h: 24小时涨跌幅
            - high_24h: 24小时最高价
            - low_24h: 24小时最低价
            - timestamp: 时间戳
            - raw: 原始数据（保留用于调试）
        """
        formatted = {
            "type": "ticker",
            "timestamp": time.time(),
            "raw": raw_ticker  # 保留原始数据
        }
        
        # 尝试从不同可能的响应结构中提取数据
        data = raw_ticker.get("data", raw_ticker)
        
        # 提取交易对信息
        if pair:
            formatted["pair"] = pair
        elif "pair" in data:
            formatted["pair"] = data["pair"]
        elif "symbol" in data:
            formatted["pair"] = data["symbol"]
        
        # 提取价格信息
        if "price" in data:
            formatted["price"] = float(data["price"])
        elif "lastPrice" in data:
            formatted["price"] = float(data["lastPrice"])
        elif "close" in data:
            formatted["price"] = float(data["close"])
        
        # 提取24小时数据
        if "volume24h" in data:
            formatted["volume_24h"] = float(data["volume24h"])
        elif "volume" in data:
            formatted["volume_24h"] = float(data["volume"])
        
        if "change24h" in data:
            formatted["change_24h"] = float(data["change24h"])
        elif "priceChangePercent" in data:
            formatted["change_24h"] = float(data["priceChangePercent"])
        
        if "high24h" in data:
            formatted["high_24h"] = float(data["high24h"])
        elif "high" in data:
            formatted["high_24h"] = float(data["high"])
        
        if "low24h" in data:
            formatted["low_24h"] = float(data["low24h"])
        elif "low" in data:
            formatted["low_24h"] = float(data["low"])
        
        return formatted
    
    @staticmethod
    def format_balance(raw_balance: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化账户余额数据
        
        Args:
            raw_balance: Roostoo API返回的原始余额数据
            
        Returns:
            格式化的余额数据，包含：
            - total_balance: 总余额
            - available_balance: 可用余额
            - currencies: 各币种余额详情
            - timestamp: 时间戳
            - raw: 原始数据
        """
        formatted = {
            "type": "balance",
            "timestamp": time.time(),
            "raw": raw_balance
        }
        
        data = raw_balance.get("data", raw_balance)
        
        # 提取总余额和可用余额
        if "totalBalance" in data:
            formatted["total_balance"] = float(data["totalBalance"])
        if "availableBalance" in data:
            formatted["available_balance"] = float(data["availableBalance"])
        
        # 提取各币种余额
        currencies = {}
        if "balances" in data:
            for balance_item in data["balances"]:
                currency = balance_item.get("currency", "UNKNOWN")
                currencies[currency] = {
                    "available": float(balance_item.get("available", 0)),
                    "locked": float(balance_item.get("locked", 0)),
                    "total": float(balance_item.get("total", 0))
                }
        formatted["currencies"] = currencies
        
        return formatted
    
    @staticmethod
    def format_exchange_info(raw_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化交易所信息
        
        Args:
            raw_info: Roostoo API返回的原始交易所信息
            
        Returns:
            格式化的交易所信息
        """
        formatted = {
            "type": "exchange_info",
            "timestamp": time.time(),
            "raw": raw_info
        }
        
        data = raw_info.get("data", raw_info)
        
        if "TradePairs" in data:
            formatted["trade_pairs"] = list(data["TradePairs"].keys())
        
        return formatted
    
    @staticmethod
    def create_market_snapshot(
        ticker: Optional[Dict[str, Any]] = None,
        balance: Optional[Dict[str, Any]] = None,
        exchange_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建综合市场快照，包含当前市场状态和账户状态
        
        Args:
            ticker: 格式化的ticker数据
            balance: 格式化的余额数据
            exchange_info: 格式化的交易所信息
            
        Returns:
            综合市场快照
        """
        snapshot = {
            "type": "market_snapshot",
            "timestamp": time.time(),
            "ticker": ticker,
            "balance": balance,
            "exchange_info": exchange_info
        }
        return snapshot
    
    @staticmethod
    def format_for_llm(snapshot: Dict[str, Any]) -> str:
        """
        将市场快照格式化为LLM可读的文本格式
        
        Args:
            snapshot: 市场快照数据
            
        Returns:
            格式化的文本描述
        """
        lines = []
        
        if snapshot.get("ticker"):
            ticker = snapshot["ticker"]
            lines.append(f"📊 Market Data ({ticker.get('pair', 'N/A')}):")
            if "price" in ticker:
                lines.append(f"  Current Price: ${ticker['price']:.2f}")
            if "change_24h" in ticker:
                change = ticker["change_24h"]
                sign = "+" if change >= 0 else ""
                lines.append(f"  24h Change: {sign}{change:.2f}%")
            if "volume_24h" in ticker:
                lines.append(f"  24h Volume: {ticker['volume_24h']:.2f}")
            if "high_24h" in ticker and "low_24h" in ticker:
                lines.append(f"  24h Range: ${ticker['low_24h']:.2f} - ${ticker['high_24h']:.2f}")
        
        if snapshot.get("balance"):
            balance = snapshot["balance"]
            lines.append(f"\n💰 Account Balance:")
            if "total_balance" in balance:
                lines.append(f"  Total Balance: ${balance['total_balance']:.2f}")
            if "available_balance" in balance:
                lines.append(f"  Available: ${balance['available_balance']:.2f}")
            if "currencies" in balance:
                lines.append(f"  Currencies:")
                for currency, amounts in balance["currencies"].items():
                    if amounts.get("total", 0) > 0:
                        lines.append(f"    {currency}: {amounts['total']:.4f} (Available: {amounts['available']:.4f})")
        
        return "\n".join(lines) if lines else "No market data available"

