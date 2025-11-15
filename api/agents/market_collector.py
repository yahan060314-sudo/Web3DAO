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
from .history_storage import HistoryStorage


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
        collect_ticker: bool = True,
        decision_topic: Optional[str] = None,
        wait_for_decisions: bool = True,
        decision_wait_timeout: float = 120.0
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
        
        # 历史数据存储（用于计算技术指标）
        self.history_storage = HistoryStorage(max_history_size=1000)
        
        # 缓存上次采集的数据，用于对比变化
        self._last_tickers: Dict[str, Dict[str, Any]] = {}
        self._last_balance: Optional[Dict[str, Any]] = None
        
        # 批处理相关属性（用于处理大量交易对时的分批采集）
        self._current_batch_index = 0
        self._batch_size = 10  # 每批处理的交易对数量，避免一次性请求过多
        
        # 完整快照发布相关
        self._last_complete_snapshot_time = 0  # 上次发布完整快照的时间
        self._complete_snapshot_interval = 600  # 每10分钟发布一次完整快照（或采集完一轮后）
        
        # 决策等待相关
        self.decision_topic = decision_topic  # 决策topic，用于监听Agent决策
        self.wait_for_decisions = wait_for_decisions  # 是否等待Agent决策完成
        self.decision_wait_timeout = decision_wait_timeout  # 等待决策的超时时间（秒）
        self._decision_subscription = None  # 决策订阅（用于监听决策）
        if self.decision_topic and self.wait_for_decisions:
            self._decision_subscription = bus.subscribe(decision_topic)
    
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
        """采集所有配置的交易对的ticker数据（分批处理以避免API限制）"""
        if not self.pairs:
            return
        
        # 计算当前批次的范围
        total_pairs = len(self.pairs)
        start_idx = self._current_batch_index * self._batch_size
        end_idx = min(start_idx + self._batch_size, total_pairs)
        
        # 获取当前批次要处理的交易对
        current_batch = self.pairs[start_idx:end_idx]
        
        # 处理当前批次
        for pair in current_batch:
            try:
                raw_ticker = self.client.get_ticker(pair=pair)
                formatted_ticker = self.formatter.format_ticker(raw_ticker, pair=pair)
                
                # 重要：每次采集都存储历史数据（无论价格是否变化）
                # 这样才能积累足够的数据点来计算技术指标
                if "price" in formatted_ticker:
                    self.history_storage.add_ticker(pair, formatted_ticker)
                    # 调试：显示历史数据点数量
                    price_series = self.history_storage.get_price_series(pair)
                    if len(price_series) % 5 == 0 or len(price_series) <= 3:  # 每5个点或前3个点打印一次
                        print(f"[MarketDataCollector] {pair}: 历史数据点数量 = {len(price_series)}")
                    
                    # 重要：无论价格是否变化，都更新_last_tickers
                    # 这样完整快照才能包含所有交易对，从而计算所有交易对的技术指标
                    self._last_tickers[pair] = formatted_ticker
                
                # 检查是否有价格变化（只在价格变化时发布到消息总线，减少消息量）
                last_ticker = self._last_tickers.get(pair)
                price_changed = True
                if last_ticker and "price" in last_ticker and "price" in formatted_ticker:
                    price_changed = abs(last_ticker["price"] - formatted_ticker["price"]) > 0.01
                
                if price_changed:
                    # 发布单个ticker数据（只在价格变化时发布，减少消息量）
                    self.bus.publish(self.market_topic, formatted_ticker)
                    print(f"[MarketDataCollector] Published ticker for {pair}: ${formatted_ticker.get('price', 'N/A')}")
                
            except Exception as e:
                print(f"[MarketDataCollector] Error fetching ticker for {pair}: {e}")
        
        # 更新批次索引，循环处理所有交易对
        self._current_batch_index += 1
        batches_needed = (total_pairs + self._batch_size - 1) // self._batch_size
        
        # 检查是否完成了一轮采集
        if self._current_batch_index >= batches_needed:
            # 完成了一轮采集，发布完整的市场快照
            self._publish_complete_snapshot()
            self._current_batch_index = 0  # 重置，开始新一轮循环
    
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
    
    def _publish_complete_snapshot(self):
        """
        发布完整的市场快照（包含所有已采集的ticker数据）
        在完成一轮采集后调用，触发Agent进行完整分析
        """
        if not self._last_tickers:
            return  # 没有ticker数据，不发布
        
        # 创建完整的市场快照（包含所有ticker和技术指标）
        complete_snapshot = self.formatter.create_market_snapshot(
            tickers=self._last_tickers,  # 使用所有已采集的ticker
            balance=self._last_balance,
            history_storage=self.history_storage  # 传入历史数据存储，用于计算技术指标
        )
        
        # 标记为完整快照（确保类型和标记都正确设置）
        complete_snapshot["type"] = "complete_market_snapshot"
        complete_snapshot["is_complete"] = True
        complete_snapshot["total_pairs_collected"] = len(self._last_tickers)
        complete_snapshot["total_pairs_available"] = len(self.pairs)
        
        # 调试：打印快照的关键信息
        print(f"[MarketDataCollector] 🔔 准备发布完整市场快照:")
        print(f"  - type: {complete_snapshot.get('type')}")
        print(f"  - is_complete: {complete_snapshot.get('is_complete')}")
        print(f"  - tickers数量: {len(self._last_tickers)}")
        print(f"  - 快照keys: {list(complete_snapshot.keys())[:10]}")
        
        # 发布完整快照
        print(f"[MarketDataCollector] 📤 正在发布完整市场快照到消息总线 (topic: {self.market_topic})...")
        self.bus.publish(self.market_topic, complete_snapshot)
        print(f"[MarketDataCollector] ✓ 已发布完整市场快照到消息总线: {len(self._last_tickers)}/{len(self.pairs)} 个交易对已采集")
        print(f"[MarketDataCollector] 📋 快照消息内容: type={complete_snapshot.get('type')}, is_complete={complete_snapshot.get('is_complete')}, tickers数量={len(complete_snapshot.get('tickers', {}))}")
        self._last_complete_snapshot_time = time.time()
        
        # 给Agent一些时间接收消息（避免消息还在队列中时就开始等待）
        print(f"[MarketDataCollector] ⏸️ 等待1秒，让Agent有时间接收完整快照消息...")
        time.sleep(1.0)
        
        # 如果启用了等待决策功能，等待Agent分析并做出决策
        if self.wait_for_decisions and self._decision_subscription:
            print(f"[MarketDataCollector] ⏳ 等待Agent分析完整快照并做出决策（最多等待 {self.decision_wait_timeout} 秒）...")
            self._wait_for_agent_decisions()
    
    def _wait_for_agent_decisions(self):
        """
        等待Agent分析完整快照并做出决策
        监听decision_topic，等待至少一个Agent做出决策，或超时
        """
        if not self._decision_subscription:
            return
        
        start_time = time.time()
        decisions_received = 0
        max_decisions = 2  # 最多等待2个Agent的决策（如果有2个Agent）
        
        print(f"[MarketDataCollector] 🔔 开始监听Agent决策...")
        
        while (time.time() - start_time) < self.decision_wait_timeout:
            # 非阻塞接收决策消息
            decision_msg = self._decision_subscription.recv(timeout=1.0)
            if decision_msg is not None:
                agent_name = decision_msg.get("agent", "unknown")
                decision_text = decision_msg.get("decision", "")
                # 只显示前100个字符，避免日志过长
                decision_preview = decision_text[:100] + "..." if len(decision_text) > 100 else decision_text
                print(f"[MarketDataCollector] ✓ 收到Agent决策: {agent_name} - {decision_preview}")
                decisions_received += 1
                
                # 如果收到了足够的决策（每个Agent一个），可以提前结束
                if decisions_received >= max_decisions:
                    print(f"[MarketDataCollector] ✓ 已收到 {decisions_received} 个Agent的决策，继续下一轮采集")
                    return
            
            # 每5秒打印一次等待状态
            elapsed = time.time() - start_time
            if int(elapsed) % 5 == 0 and elapsed > 0:
                print(f"[MarketDataCollector] ⏳ 等待中... ({int(elapsed)}/{int(self.decision_wait_timeout)} 秒)")
        
        elapsed = time.time() - start_time
        if decisions_received > 0:
            print(f"[MarketDataCollector] ✓ 等待完成: 收到 {decisions_received} 个决策，耗时 {elapsed:.1f} 秒，继续下一轮采集")
        else:
            print(f"[MarketDataCollector] ⚠️ 等待超时: {elapsed:.1f} 秒内未收到Agent决策，继续下一轮采集")
    
    def get_latest_snapshot(self) -> Dict[str, Any]:
        """
        获取最新的市场快照（包含所有ticker和余额）
        
        Returns:
            综合市场快照
        """
        return self.formatter.create_market_snapshot(
            tickers=self._last_tickers,  # 返回所有ticker，而不是单个
            balance=self._last_balance
        )









