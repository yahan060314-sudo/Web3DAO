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
        collect_interval: float = None,
        collect_balance: bool = True,
        collect_ticker: bool = True,
        auto_discover_pairs: bool = True,
        batch_size: int = 3
    ):
        """
        初始化市场数据采集器
        
        Args:
            bus: 消息总线实例
            market_topic: 市场数据发布到的topic名称
            pairs: 要采集的交易对列表，如果为None且auto_discover_pairs=True，则自动获取所有可用交易对
            collect_interval: 采集间隔（秒），如果为None则根据交易对数量自动计算
            collect_balance: 是否采集账户余额，默认True
            collect_ticker: 是否采集ticker数据，默认True
            auto_discover_pairs: 是否自动发现所有可用交易对，默认True
            batch_size: 每次循环采集的交易对数量（分批采集），默认3个
        """
        super().__init__(name="MarketDataCollector")
        self.daemon = True
        self.bus = bus
        self.market_topic = market_topic
        self.collect_balance = collect_balance
        self.collect_ticker = collect_ticker
        self.auto_discover_pairs = auto_discover_pairs
        self.batch_size = batch_size
        
        self.client = RoostooClient()
        self.formatter = DataFormatter()
        self._stopped = False
        
        # 缓存上次采集的数据，用于对比变化
        self._last_tickers: Dict[str, Dict[str, Any]] = {}
        self._last_balance: Optional[Dict[str, Any]] = None
        self._last_exchange_info: Optional[Dict[str, Any]] = None
        
        # 分批采集相关
        self._current_batch_index = 0  # 当前批次索引
        
        # 初始化交易对列表
        if pairs is not None:
            self.pairs = pairs
        elif auto_discover_pairs:
            # 自动获取所有可用交易对
            self.pairs = self._discover_available_pairs()
            print(f"[MarketDataCollector] 自动发现 {len(self.pairs)} 个可用交易对: {', '.join(self.pairs[:10])}{'...' if len(self.pairs) > 10 else ''}")
        else:
            self.pairs = ["BTC/USD"]
            print(f"[MarketDataCollector] 使用默认交易对: BTC/USD")
        
        # 自动计算采集间隔（如果未指定）
        if collect_interval is None:
            # 根据交易对数量和API限频自动计算
            # API限频：每分钟最多3次（从 utils/rate_limiter.py 读取）
            from utils.rate_limiter import API_RATE_LIMITER
            max_calls_per_minute = API_RATE_LIMITER.max_calls
            time_window = API_RATE_LIMITER.time_window
            
            # 每次循环需要的API调用次数
            calls_per_cycle = self.batch_size + (1 if self.collect_balance else 0)
            
            # 计算理论最小间隔：确保每分钟的总调用次数不超过限制
            # 公式：interval = (time_window / max_calls_per_minute) * calls_per_cycle
            # 但考虑到频率限制器会自动控制等待，我们可以使用更宽松的计算
            # 使用安全系数1.2，确保有缓冲
            theoretical_min_interval = (time_window / max_calls_per_minute) * calls_per_cycle * 1.2
            
            # 设置最小间隔为20秒（避免过于频繁），最大间隔为60秒（避免数据过旧）
            self.collect_interval = max(20.0, min(60.0, theoretical_min_interval))
            
            # 计算完整轮换一次需要的时间
            cycles_per_rotation = (len(self.pairs) + self.batch_size - 1) // self.batch_size
            rotation_time = cycles_per_rotation * self.collect_interval
            
            print(f"[MarketDataCollector] 自动计算采集间隔: {self.collect_interval:.1f}秒")
            print(f"  - 交易对数量: {len(self.pairs)}")
            print(f"  - 批次大小: {self.batch_size} 个/循环")
            print(f"  - 每次循环API调用: {calls_per_cycle} 次 (ticker: {self.batch_size}, balance: {1 if self.collect_balance else 0})")
            print(f"  - API限频: {max_calls_per_minute}次/{time_window:.0f}秒")
            print(f"  - 完整轮换: {cycles_per_rotation} 个循环 ({rotation_time:.1f}秒)")
        else:
            self.collect_interval = collect_interval
    
    def stop(self):
        """停止采集器"""
        self._stopped = True
    
    def _discover_available_pairs(self) -> List[str]:
        """
        自动发现所有可用的交易对
        
        Returns:
            可用交易对列表
        """
        try:
            exchange_info = self.client.get_exchange_info()
            # 处理不同的API响应格式
            trade_pairs = {}
            if "TradePairs" in exchange_info:
                trade_pairs = exchange_info["TradePairs"]
            elif "data" in exchange_info and "TradePairs" in exchange_info["data"]:
                trade_pairs = exchange_info["data"]["TradePairs"]
            
            if trade_pairs:
                pairs_list = list(trade_pairs.keys())
                print(f"[MarketDataCollector] 发现 {len(pairs_list)} 个可用交易对")
                return pairs_list
            else:
                print(f"[MarketDataCollector] ⚠️ 无法获取交易对列表，使用默认 BTC/USD")
                return ["BTC/USD"]
        except Exception as e:
            print(f"[MarketDataCollector] ⚠️ 获取交易对列表失败: {e}，使用默认 BTC/USD")
            return ["BTC/USD"]
    
    def run(self):
        """主循环：定期采集数据并发布"""
        print(f"[MarketDataCollector] Started. Collecting data every {self.collect_interval:.1f}s")
        print(f"[MarketDataCollector] Monitoring {len(self.pairs)} trading pairs")
        print(f"[MarketDataCollector] Batch size: {self.batch_size} pairs per cycle")
        
        # 计算完整轮换一次需要多少循环
        if self.pairs:
            cycles_per_rotation = (len(self.pairs) + self.batch_size - 1) // self.batch_size
            rotation_time = cycles_per_rotation * self.collect_interval
            print(f"[MarketDataCollector] Full rotation: {cycles_per_rotation} cycles ({rotation_time:.1f}s)")
        
        # 首次采集交易所信息
        if self.auto_discover_pairs:
            self._collect_exchange_info()
        
        iteration = 0
        while not self._stopped:
            try:
                # 定期更新交易所信息（每20次循环更新一次，避免频繁调用）
                # 如果交易对数量很多，可能需要更频繁地更新
                exchange_info_interval = max(20, len(self.pairs) // self.batch_size * 2)
                if self.auto_discover_pairs and iteration % exchange_info_interval == 0:
                    self._collect_exchange_info()
                
                # 采集ticker数据（分批采集）
                if self.collect_ticker:
                    self._collect_tickers()
                
                # 采集余额数据（每次循环都采集，但频率限制器会控制）
                if self.collect_balance:
                    self._collect_balance()
                
                iteration += 1
            except Exception as e:
                print(f"[MarketDataCollector] Error collecting data: {e}")
            
            # 等待下次采集
            time.sleep(self.collect_interval)
        
        print("[MarketDataCollector] Stopped")
    
    def _collect_tickers(self):
        """
        分批采集交易对的ticker数据
        
        每次循环只采集一部分交易对，轮换采集所有交易对
        这样可以避免单次循环调用太多API，同时确保所有交易对都能被采集到
        """
        if not self.pairs:
            return
        
        # 计算本次要采集的交易对批次
        num_pairs = len(self.pairs)
        start_idx = self._current_batch_index
        end_idx = min(start_idx + self.batch_size, num_pairs)
        
        # 获取本次要采集的交易对
        pairs_to_collect = self.pairs[start_idx:end_idx]
        
        # 如果到达末尾，从头开始
        if end_idx >= num_pairs:
            self._current_batch_index = 0
        else:
            self._current_batch_index = end_idx
        
        # 采集这批交易对的数据
        for pair in pairs_to_collect:
            try:
                raw_ticker = self.client.get_ticker(pair=pair)
                formatted_ticker = self.formatter.format_ticker(raw_ticker, pair=pair)
                
                # 检查是否有价格变化（只在价格变化时发布，减少重复数据）
                last_ticker = self._last_tickers.get(pair)
                price_changed = True
                if last_ticker and "price" in last_ticker and "price" in formatted_ticker:
                    # 如果价格变化超过0.1%，则发布更新
                    price_change_pct = abs((formatted_ticker["price"] - last_ticker["price"]) / last_ticker["price"]) * 100
                    price_changed = price_change_pct > 0.1  # 0.1%的变化阈值
                
                # 更新缓存（无论是否发布都要更新，以便下次比较）
                self._last_tickers[pair] = formatted_ticker
                
                if price_changed:
                    # 发布单个ticker数据
                    self.bus.publish(self.market_topic, formatted_ticker)
                    if last_ticker:
                        change_pct = ((formatted_ticker["price"] - last_ticker["price"]) / last_ticker["price"]) * 100
                        print(f"[MarketDataCollector] Published ticker for {pair}: ${formatted_ticker.get('price', 'N/A'):.2f} ({change_pct:+.2f}%)")
                    else:
                        print(f"[MarketDataCollector] Published ticker for {pair}: ${formatted_ticker.get('price', 'N/A'):.2f}")
                
            except Exception as e:
                print(f"[MarketDataCollector] Error fetching ticker for {pair}: {e}")
        
        # 计算完整轮换一次需要多少循环
        cycles_per_rotation = (num_pairs + self.batch_size - 1) // self.batch_size  # 向上取整
        if cycles_per_rotation > 1:
            current_cycle = (start_idx // self.batch_size) + 1
            print(f"[MarketDataCollector] 批次进度: {current_cycle}/{cycles_per_rotation} (本次采集: {', '.join(pairs_to_collect)})")
    
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
    
    def _collect_exchange_info(self):
        """采集交易所信息（包含所有可用交易对）"""
        try:
            raw_exchange_info = self.client.get_exchange_info()
            formatted_exchange_info = self.formatter.format_exchange_info(raw_exchange_info)
            
            # 检查交易对列表是否有变化
            exchange_info_changed = True
            if self._last_exchange_info and formatted_exchange_info.get("trade_pairs"):
                last_pairs = set(self._last_exchange_info.get("trade_pairs", []))
                current_pairs = set(formatted_exchange_info.get("trade_pairs", []))
                exchange_info_changed = last_pairs != current_pairs
            
            if exchange_info_changed:
                self._last_exchange_info = formatted_exchange_info
                # 发布交易所信息
                self.bus.publish(self.market_topic, formatted_exchange_info)
                
                # 如果启用了自动发现，更新交易对列表
                if self.auto_discover_pairs and formatted_exchange_info.get("trade_pairs"):
                    new_pairs = formatted_exchange_info["trade_pairs"]
                    if set(new_pairs) != set(self.pairs):
                        self.pairs = new_pairs
                        print(f"[MarketDataCollector] 交易对列表已更新: {len(self.pairs)} 个交易对")
                
                print(f"[MarketDataCollector] Published exchange info: {len(formatted_exchange_info.get('trade_pairs', []))} trading pairs")
                
        except Exception as e:
            print(f"[MarketDataCollector] Error fetching exchange info: {e}")
    
    def get_latest_snapshot(self) -> Dict[str, Any]:
        """
        获取最新的市场快照（包含所有ticker和余额）
        
        Returns:
            综合市场快照
        """
        # 传递所有ticker数据（作为字典）而不是单个ticker
        tickers_dict = self._last_tickers if self._last_tickers else None
        return self.formatter.create_market_snapshot(
            tickers=tickers_dict,
            balance=self._last_balance,
            exchange_info=self._last_exchange_info
        )

