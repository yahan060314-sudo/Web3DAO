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
from .technical_indicators import TechnicalIndicators


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
        
        # Roostoo API返回格式: {'Success': True, 'Data': {'BTC/USD': {...}}}
        # 需要处理嵌套结构
        data = raw_ticker.get("Data", raw_ticker.get("data", raw_ticker))
        
        # 如果data是字典且包含交易对作为key（如 {'BTC/USD': {...}}）
        # 需要提取交易对的数据
        pair_data = None
        if isinstance(data, dict):
            # 检查是否是嵌套结构：data = {'BTC/USD': {...}}
            if pair and pair in data:
                pair_data = data[pair]
                formatted["pair"] = pair
            elif len(data) == 1 and isinstance(list(data.values())[0], dict):
                # 只有一个key，且value是字典，可能是交易对数据
                pair_key = list(data.keys())[0]
                pair_data = data[pair_key]
                formatted["pair"] = pair_key
            else:
                # 直接使用data
                pair_data = data
                if pair:
                    formatted["pair"] = pair
                elif "pair" in data:
                    formatted["pair"] = data["pair"]
                elif "symbol" in data:
                    formatted["pair"] = data["symbol"]
        else:
            pair_data = data
        
        # 从pair_data中提取价格信息
        if pair_data:
            # 提取价格信息（Roostoo使用LastPrice）
            if "LastPrice" in pair_data:
                formatted["price"] = float(pair_data["LastPrice"])
            elif "price" in pair_data:
                formatted["price"] = float(pair_data["price"])
            elif "lastPrice" in pair_data:
                formatted["price"] = float(pair_data["lastPrice"])
            elif "close" in pair_data:
                formatted["price"] = float(pair_data["close"])
            
            # 提取24小时数据
            # Roostoo可能使用CoinTradeValue作为成交量
            if "UnitTradeValue" in pair_data:
                formatted["volume_24h"] = float(pair_data["UnitTradeValue"])
            elif "CoinTradeValue" in pair_data:
                formatted["volume_24h"] = float(pair_data["CoinTradeValue"])
            elif "volume24h" in pair_data:
                formatted["volume_24h"] = float(pair_data["volume24h"])
            elif "volume" in pair_data:
                formatted["volume_24h"] = float(pair_data["volume"])
            
            # 提取涨跌幅（Roostoo使用Change，可能是小数形式如0.0189表示1.89%）
            if "Change" in pair_data:
                change_value = float(pair_data["Change"])
                # 如果是小数形式（如0.0189），转换为百分比
                if abs(change_value) < 1:
                    formatted["change_24h"] = change_value * 100
                else:
                    formatted["change_24h"] = change_value
            elif "change24h" in pair_data:
                formatted["change_24h"] = float(pair_data["change24h"])
            elif "priceChangePercent" in pair_data:
                formatted["change_24h"] = float(pair_data["priceChangePercent"])
            
            # 提取最高价和最低价（Roostoo使用MaxBid和MinAsk）
            if "MaxBid" in pair_data and "MinAsk" in pair_data:
                formatted["high_24h"] = max(float(pair_data["MaxBid"]), float(pair_data["MinAsk"]))
                formatted["low_24h"] = min(float(pair_data["MaxBid"]), float(pair_data["MinAsk"]))
            elif "high24h" in pair_data:
                formatted["high_24h"] = float(pair_data["high24h"])
            elif "high" in pair_data:
                formatted["high_24h"] = float(pair_data["high"])
            
            if "low24h" in pair_data:
                formatted["low_24h"] = float(pair_data["low24h"])
            elif "low" in pair_data:
                formatted["low_24h"] = float(pair_data["low"])
        
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
        
        # Roostoo API返回格式: {'Success': True, 'SpotWallet': {'USD': {'Free': 50000, 'Lock': 0}}, ...}
        data = raw_balance.get("data", raw_balance)
        
        # 处理Roostoo的SpotWallet格式
        spot_wallet = data.get("SpotWallet", {})
        if spot_wallet:
            currencies = {}
            total_balance = 0.0
            available_balance = 0.0
            
            for currency, wallet_info in spot_wallet.items():
                if isinstance(wallet_info, dict):
                    free = float(wallet_info.get("Free", 0))
                    locked = float(wallet_info.get("Lock", 0))
                    total = free + locked
                    
                    currencies[currency] = {
                        "available": free,
                        "locked": locked,
                        "total": total
                    }
                    
                    total_balance += total
                    available_balance += free
            
            formatted["currencies"] = currencies
            formatted["total_balance"] = total_balance
            formatted["available_balance"] = available_balance
        else:
            # 尝试其他格式
            if "totalBalance" in data:
                formatted["total_balance"] = float(data["totalBalance"])
            if "availableBalance" in data:
                formatted["available_balance"] = float(data["availableBalance"])
            
            # 提取各币种余额（其他格式）
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
        tickers: Optional[Dict[str, Dict[str, Any]]] = None,
        balance: Optional[Dict[str, Any]] = None,
        exchange_info: Optional[Dict[str, Any]] = None,
        history_storage=None
    ) -> Dict[str, Any]:
        """
        创建综合市场快照，包含当前市场状态和账户状态
        
        Args:
            ticker: 单个格式化的ticker数据（向后兼容）
            tickers: 多个ticker数据的字典（pair -> ticker data），优先级高于ticker
            balance: 格式化的余额数据
            exchange_info: 格式化的交易所信息
            
        Returns:
            综合市场快照
        """
        # 如果提供了tickers字典，使用它；否则使用单个ticker（向后兼容）
        if tickers is not None and isinstance(tickers, dict) and len(tickers) > 0:
            # 多个ticker数据 - 为每个ticker添加技术指标
            tickers_with_indicators = {}
            for pair, ticker_data in tickers.items():
                ticker_with_indicators = ticker_data.copy()
                # 如果有历史数据存储，计算技术指标
                if history_storage:
                    try:
                        price_series = history_storage.get_price_series(pair, limit=500)
                        data_count = len(price_series)
                        if data_count >= 14:  # 至少需要14个数据点来计算RSI等指标
                            indicators = TechnicalIndicators.calculate_all_indicators(price_series)
                            ticker_with_indicators['indicators'] = indicators
                            # 调试：确认指标已计算
                            if indicators.get('rsi') is not None:
                                print(f"[DataFormatter] ✓ {pair}: 完整技术指标已计算 (历史数据: {data_count}点, RSI={indicators['rsi']:.2f})")
                        elif data_count >= 2:  # 数据不足但至少有2个点，计算部分指标
                            indicators = TechnicalIndicators.calculate_partial_indicators(price_series)
                            ticker_with_indicators['indicators'] = indicators
                            # 显示可用的指标
                            available_indicators = [k for k, v in indicators.items() if v is not None]
                            if available_indicators:
                                print(f"[DataFormatter] ⚠️ {pair}: 部分技术指标已计算 (历史数据: {data_count}点, 可用指标: {', '.join(available_indicators[:5])})")
                            else:
                                print(f"[DataFormatter] ⚠️ {pair}: 历史数据不足 ({data_count}点)，无法计算技术指标")
                        else:
                            # 数据太少（少于2个点），不计算指标
                            if data_count > 0:
                                print(f"[DataFormatter] ⚠️ {pair}: 历史数据太少 ({data_count}点)，无法计算技术指标")
                    except Exception as e:
                        # 计算指标失败不影响主流程，但打印错误以便调试
                        print(f"[DataFormatter] ⚠️ {pair}: 计算技术指标失败: {e}")
                        import traceback
                        traceback.print_exc()
                tickers_with_indicators[pair] = ticker_with_indicators
            
            snapshot = {
                "type": "market_snapshot",
                "timestamp": time.time(),
                "tickers": tickers_with_indicators,  # 包含技术指标的多个ticker数据
                "ticker": list(tickers_with_indicators.values())[0] if tickers_with_indicators else None,  # 向后兼容
                "balance": balance,
                "exchange_info": exchange_info
            }
        else:
            # 单个ticker数据（向后兼容）
            ticker_with_indicators = ticker.copy() if ticker else None
            if ticker_with_indicators and history_storage:
                pair = ticker_with_indicators.get("pair")
                if pair:
                    try:
                        price_series = history_storage.get_price_series(pair, limit=500)
                        data_count = len(price_series)
                        if data_count >= 14:
                            indicators = TechnicalIndicators.calculate_all_indicators(price_series)
                            ticker_with_indicators['indicators'] = indicators
                            if indicators.get('rsi') is not None:
                                print(f"[DataFormatter] ✓ {pair}: 技术指标已计算 (历史数据: {data_count}点)")
                        else:
                            if data_count > 0:
                                print(f"[DataFormatter] ⚠️ {pair}: 历史数据不足 ({data_count}/14点)，无法计算技术指标")
                    except Exception as e:
                        print(f"[DataFormatter] ⚠️ {pair}: 计算技术指标失败: {e}")
            
            snapshot = {
                "type": "market_snapshot",
                "timestamp": time.time(),
                "ticker": ticker_with_indicators,
                "tickers": {ticker_with_indicators.get("pair"): ticker_with_indicators} if ticker_with_indicators and ticker_with_indicators.get("pair") else None,
                "balance": balance,
                "exchange_info": exchange_info
            }
        return snapshot
    
    @staticmethod
    def format_for_llm(snapshot: Dict[str, Any]) -> str:
        """
        将市场快照格式化为LLM可读的文本格式
        
        Args:
            snapshot: 市场快照数据（可能包含单个ticker或多个tickers）
            
        Returns:
            格式化的文本描述
        """
        lines = []
        
        # 支持多个ticker数据（如果snapshot包含tickers字典）
        tickers_to_format = []
        if snapshot.get("tickers") and isinstance(snapshot["tickers"], dict):
            # 如果有多个tickers，格式化所有
            tickers_to_format = list(snapshot["tickers"].values())
        elif snapshot.get("ticker"):
            # 单个ticker（保持向后兼容）
            tickers_to_format = [snapshot["ticker"]]
        
        # 格式化所有ticker数据
        if tickers_to_format:
            if len(tickers_to_format) == 1:
                # 单个币种，保持原有格式
                ticker = tickers_to_format[0]
                pair = ticker.get('pair', 'N/A')
                lines.append(f"📊 Market Data ({pair}):")
                
                # 检查price字段（可能在不同位置）
                price = ticker.get("price") or ticker.get("Price") or ticker.get("lastPrice")
                if price is not None:
                    try:
                        lines.append(f"  Current Price: ${float(price):.2f}")
                    except (ValueError, TypeError):
                        # 如果转换失败，至少显示原始值
                        lines.append(f"  Current Price: {price} (raw)")
                else:
                    # 即使没有price，也显示ticker数据存在，并显示可用的字段
                    available_fields = [k for k in ticker.keys() if k not in ['type', 'timestamp', 'raw', 'pair']]
                    lines.append(f"  Market data available for {pair}")
                    if available_fields:
                        lines.append(f"  Available fields: {', '.join(available_fields[:5])}")
                
                if "change_24h" in ticker:
                    change = ticker["change_24h"]
                    sign = "+" if change >= 0 else ""
                    lines.append(f"  24h Change: {sign}{change:.2f}%")
                if "volume_24h" in ticker:
                    lines.append(f"  24h Volume: {ticker['volume_24h']:.2f}")
                if "high_24h" in ticker and "low_24h" in ticker:
                    lines.append(f"  24h Range: ${ticker['low_24h']:.2f} - ${ticker['high_24h']:.2f}")
                
                # 添加技术指标信息
                if "indicators" in ticker and ticker["indicators"]:
                    indicators = ticker["indicators"]
                    # 检查是否有任何非None的指标值
                    has_any_indicator = any(v is not None for v in indicators.values())
                    if has_any_indicator:
                        lines.append(f"  📈 Technical Indicators:")
                        # 价格趋势（部分指标）
                        if indicators.get("price_trend") is not None:
                            trend = indicators['price_trend']
                            change_pct = indicators.get('price_change_pct', 0)
                            lines.append(f"    Price Trend: {trend.upper()} ({change_pct:+.2f}%)")
                        # 短周期指标（部分指标）
                        if indicators.get("sma_3") is not None:
                            lines.append(f"    SMA(3): ${indicators['sma_3']:.2f}")
                        if indicators.get("sma_5") is not None:
                            lines.append(f"    SMA(5): ${indicators['sma_5']:.2f}")
                        if indicators.get("ema_3") is not None:
                            lines.append(f"    EMA(3): ${indicators['ema_3']:.2f}")
                        if indicators.get("ema_5") is not None:
                            lines.append(f"    EMA(5): ${indicators['ema_5']:.2f}")
                        if indicators.get("ema_9") is not None:
                            lines.append(f"    EMA(9): ${indicators['ema_9']:.2f}")
                        if indicators.get("ema_12") is not None:
                            lines.append(f"    EMA(12): ${indicators['ema_12']:.2f}")
                        # 完整指标
                        if indicators.get("rsi") is not None:
                            lines.append(f"    RSI(14): {indicators['rsi']:.2f}")
                        if indicators.get("ema_26") is not None:
                            lines.append(f"    EMA(26): ${indicators['ema_26']:.2f}")
                        if indicators.get("ema_50") is not None:
                            lines.append(f"    EMA(50): ${indicators['ema_50']:.2f}")
                        if indicators.get("macd") is not None:
                            lines.append(f"    MACD: {indicators['macd']:.4f}")
                            if indicators.get("macd_signal") is not None:
                                lines.append(f"    MACD Signal: {indicators['macd_signal']:.4f}")
                            if indicators.get("macd_histogram") is not None:
                                lines.append(f"    MACD Histogram: {indicators['macd_histogram']:.4f}")
                        if indicators.get("bb_upper") is not None and indicators.get("bb_lower") is not None:
                            lines.append(f"    Bollinger Bands: ${indicators['bb_lower']:.2f} - ${indicators['bb_upper']:.2f}")
                    else:
                        # 指标字典存在但所有值都是None
                        lines.append(f"  📈 Technical Indicators: Not available (insufficient historical data - need at least 14 data points)")
                else:
                    # 如果没有技术指标，说明数据不足或计算失败
                    lines.append(f"  📈 Technical Indicators: Not available (insufficient historical data - need at least 14 data points)")
                
                # 调试：如果没有price字段，打印ticker的keys
                if not price:
                    print(f"[DataFormatter] ⚠️ Ticker {pair} 没有price字段，keys: {list(ticker.keys())[:10]}")
            else:
                # 多个币种，格式化所有
                lines.append(f"📊 Market Data (Multiple Currencies - {len(tickers_to_format)} pairs):")
                for ticker in tickers_to_format:
                    pair = ticker.get('pair', 'N/A')
                    lines.append(f"\n  {pair}:")
                    
                    # 检查price字段（可能在不同位置）
                    price = ticker.get("price") or ticker.get("Price") or ticker.get("lastPrice")
                    if price is not None:
                        try:
                            lines.append(f"    Current Price: ${float(price):.2f}")
                        except (ValueError, TypeError):
                            # 如果转换失败，至少显示原始值
                            lines.append(f"    Current Price: {price} (raw)")
                    else:
                        # 即使没有price，也显示ticker数据存在
                        lines.append(f"    Market data available (price field not found)")
                    
                    if "change_24h" in ticker:
                        change = ticker["change_24h"]
                        sign = "+" if change >= 0 else ""
                        lines.append(f"    24h Change: {sign}{change:.2f}%")
                    if "volume_24h" in ticker:
                        lines.append(f"    24h Volume: {ticker['volume_24h']:.2f}")
                    if "high_24h" in ticker and "low_24h" in ticker:
                        lines.append(f"    24h Range: ${ticker['low_24h']:.2f} - ${ticker['high_24h']:.2f}")
                    
                    # 添加技术指标信息
                    if "indicators" in ticker and ticker["indicators"]:
                        indicators = ticker["indicators"]
                        # 检查是否有任何非None的指标值
                        has_any_indicator = any(v is not None for v in indicators.values())
                        if has_any_indicator:
                            lines.append(f"    📈 Technical Indicators:")
                            # 价格趋势（部分指标）
                            if indicators.get("price_trend") is not None:
                                trend = indicators['price_trend']
                                change_pct = indicators.get('price_change_pct', 0)
                                lines.append(f"      Price Trend: {trend.upper()} ({change_pct:+.2f}%)")
                            # 短周期指标（部分指标）
                            if indicators.get("sma_3") is not None:
                                lines.append(f"      SMA(3): ${indicators['sma_3']:.2f}")
                            if indicators.get("sma_5") is not None:
                                lines.append(f"      SMA(5): ${indicators['sma_5']:.2f}")
                            if indicators.get("ema_3") is not None:
                                lines.append(f"      EMA(3): ${indicators['ema_3']:.2f}")
                            if indicators.get("ema_5") is not None:
                                lines.append(f"      EMA(5): ${indicators['ema_5']:.2f}")
                            if indicators.get("ema_9") is not None:
                                lines.append(f"      EMA(9): ${indicators['ema_9']:.2f}")
                            if indicators.get("ema_12") is not None:
                                lines.append(f"      EMA(12): ${indicators['ema_12']:.2f}")
                            # 完整指标
                            if indicators.get("rsi") is not None:
                                lines.append(f"      RSI(14): {indicators['rsi']:.2f}")
                            if indicators.get("ema_26") is not None:
                                lines.append(f"      EMA(26): ${indicators['ema_26']:.2f}")
                            if indicators.get("ema_50") is not None:
                                lines.append(f"      EMA(50): ${indicators['ema_50']:.2f}")
                            if indicators.get("macd") is not None:
                                lines.append(f"      MACD: {indicators['macd']:.4f}")
                                if indicators.get("macd_signal") is not None:
                                    lines.append(f"      MACD Signal: {indicators['macd_signal']:.4f}")
                            if indicators.get("bb_upper") is not None and indicators.get("bb_lower") is not None:
                                lines.append(f"      Bollinger Bands: ${indicators['bb_lower']:.2f} - ${indicators['bb_upper']:.2f}")
                        else:
                            # 指标字典存在但所有值都是None
                            lines.append(f"    📈 Technical Indicators: Not available (insufficient historical data)")
                    else:
                        # 如果没有技术指标，说明数据不足或计算失败
                        lines.append(f"    📈 Technical Indicators: Not available (insufficient historical data)")
        
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
        
        # 如果有exchange_info，显示可用交易对
        if snapshot.get("exchange_info") and snapshot["exchange_info"].get("trade_pairs"):
            trade_pairs = snapshot["exchange_info"]["trade_pairs"]
            if trade_pairs:
                lines.append(f"\n📈 Available Trading Pairs ({len(trade_pairs)} total):")
                # 只显示前10个，避免prompt过长
                display_pairs = trade_pairs[:10]
                lines.append(f"  {', '.join(display_pairs)}")
                if len(trade_pairs) > 10:
                    lines.append(f"  ... and {len(trade_pairs) - 10} more pairs available")
        
        return "\n".join(lines) if lines else "No market data available"









