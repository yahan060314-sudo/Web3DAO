"""
市场数据采集器 - 定期从Roostoo获取市场数据并发布到消息总线

这个模块负责：
1. 定期从Roostoo API获取市场数据（ticker、余额等）
2. 使用DataFormatter格式化数据
3. 将格式化的数据发布到消息总线，供Agent订阅
4. 支持配置采集频率和交易对
"""

import threading
import time
from typing import Dict, Any, Optional, List
from api.roostoo_client import RoostooClient
from .bus import MessageBus
from .data_formatter import DataFormatter


class MarketDataCollector(threading.Thread):
    """
    市场数据采集器：独立线程运行，定期从Roostoo获取数据并发布到消息总线
    """
    
    def __init__(
        self,
        bus: MessageBus,
        market_topic: str,
        pairs: List[str] = None,
        collect_interval: float = 12.0,
        collect_balance: bool = True,
        collect_ticker: bool = True
    ):
        """
        初始化市场数据采集器
        
        Args:
            bus: 消息总线实例
            market_topic: 市场数据发布到的topic名称
            pairs: 要采集的交易对列表，默认 ["BTC/USD"]
            collect_interval: 采集间隔（秒），默认12秒（符合每分钟最多5次API调用的限制）
            collect_balance: 是否采集账户余额，默认True
            collect_ticker: 是否采集ticker数据，默认True
        """
        super().__init__(name="MarketDataCollector")
        self.daemon = True
        self.bus = bus
        self.market_topic = market_topic
        self.pairs = pairs or ["BTC/USD"]
        self.collect_interval = collect_interval
        self.collect_balance = collect_balance
        self.collect_ticker = collect_ticker
        
        self.client = RoostooClient()
        self.formatter = DataFormatter()
        self._stopped = False
        
        # 缓存上次采集的数据，用于对比变化
        self._last_tickers: Dict[str, Dict[str, Any]] = {}
        self._last_balance: Optional[Dict[str, Any]] = None
    
    def stop(self):
        """停止采集器"""
        self._stopped = True
    
    def run(self):
        """主循环：定期采集数据并发布"""
        print(f"[MarketDataCollector] Started. Collecting data every {self.collect_interval}s")
        
        while not self._stopped:
            try:
                # 采集ticker数据
                if self.collect_ticker:
                    self._collect_tickers()
                
                # 采集余额数据
                if self.collect_balance:
                    self._collect_balance()
                
            except Exception as e:
                print(f"[MarketDataCollector] Error collecting data: {e}")
            
            # 等待下次采集
            time.sleep(self.collect_interval)
        
        print("[MarketDataCollector] Stopped")
    
    def _collect_tickers(self):
        """采集所有配置的交易对的ticker数据"""
        for pair in self.pairs:
            try:
                raw_ticker = self.client.get_ticker(pair=pair)
                formatted_ticker = self.formatter.format_ticker(raw_ticker, pair=pair)
                
                # 检查是否有价格变化（可选：只在价格变化时发布）
                last_ticker = self._last_tickers.get(pair)
                price_changed = True
                if last_ticker and "price" in last_ticker and "price" in formatted_ticker:
                    price_changed = abs(last_ticker["price"] - formatted_ticker["price"]) > 0.01
                
                if price_changed:
                    self._last_tickers[pair] = formatted_ticker
                    # 发布单个ticker数据
                    self.bus.publish(self.market_topic, formatted_ticker)
                    print(f"[MarketDataCollector] Published ticker for {pair}: ${formatted_ticker.get('price', 'N/A')}")
                
            except Exception as e:
                print(f"[MarketDataCollector] Error fetching ticker for {pair}: {e}")
    
    def _collect_balance(self):
        """采集账户余额数据"""
        try:
            raw_balance = self.client.get_balance()
            formatted_balance = self.formatter.format_balance(raw_balance)
            
            # 检查余额是否有变化
            balance_changed = True
            if self._last_balance and "total_balance" in self._last_balance:
                if "total_balance" in formatted_balance:
                    balance_changed = abs(
                        self._last_balance["total_balance"] - formatted_balance["total_balance"]
                    ) > 0.01
            
            if balance_changed:
                self._last_balance = formatted_balance
                # 发布余额数据
                self.bus.publish(self.market_topic, formatted_balance)
                print(f"[MarketDataCollector] Published balance: ${formatted_balance.get('total_balance', 'N/A')}")
                
        except Exception as e:
            print(f"[MarketDataCollector] Error fetching balance: {e}")
    
    def get_latest_snapshot(self) -> Dict[str, Any]:
        """
        获取最新的市场快照（包含所有ticker和余额）
        
        Returns:
            综合市场快照
        """
        return self.formatter.create_market_snapshot(
            ticker=self._last_tickers.get(self.pairs[0]) if self.pairs else None,
            balance=self._last_balance
        )

