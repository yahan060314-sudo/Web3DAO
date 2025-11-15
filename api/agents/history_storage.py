"""
历史数据存储模块 - 存储和管理价格历史数据，用于计算技术指标

这个模块负责：
1. 存储每个交易对的历史价格数据（时间序列）
2. 维护固定大小的历史窗口（如最近1000个数据点）
3. 提供查询接口，获取指定时间范围的历史数据
4. 线程安全的数据访问
"""

import threading
import time
from typing import Dict, List, Optional, Any
from collections import deque
from datetime import datetime, timedelta


class HistoryStorage:
    """
    历史数据存储：使用deque实现高效的时间序列存储
    每个交易对维护一个时间序列队列
    """
    
    def __init__(self, max_history_size: int = 1000):
        """
        初始化历史数据存储
        
        Args:
            max_history_size: 每个交易对保留的最大历史数据点数量，默认1000
        """
        self.max_history_size = max_history_size
        # pair -> deque of {timestamp, price, volume, ...}
        self._history: Dict[str, deque] = {}
        self._lock = threading.Lock()
    
    def add_ticker(self, pair: str, ticker_data: Dict[str, Any]) -> None:
        """
        添加一个ticker数据点到历史记录
        
        Args:
            pair: 交易对名称（如 "BTC/USD"）
            ticker_data: ticker数据，必须包含 'price' 字段
        """
        if not ticker_data or 'price' not in ticker_data:
            return
        
        with self._lock:
            if pair not in self._history:
                self._history[pair] = deque(maxlen=self.max_history_size)
            
            # 创建历史数据点
            history_point = {
                'timestamp': time.time(),
                'price': float(ticker_data['price']),
                'volume_24h': ticker_data.get('volume_24h', 0.0),
                'change_24h': ticker_data.get('change_24h', 0.0),
                'high_24h': ticker_data.get('high_24h', ticker_data.get('price', 0.0)),
                'low_24h': ticker_data.get('low_24h', ticker_data.get('price', 0.0)),
            }
            
            # 添加到队列（deque会自动处理maxlen限制）
            self._history[pair].append(history_point)
    
    def get_history(self, pair: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取指定交易对的历史数据
        
        Args:
            pair: 交易对名称
            limit: 返回最近N个数据点，None表示返回全部
        
        Returns:
            历史数据列表，按时间从旧到新排序
        """
        with self._lock:
            if pair not in self._history:
                return []
            
            history = list(self._history[pair])
            if limit:
                return history[-limit:]
            return history
    
    def get_price_series(self, pair: str, limit: Optional[int] = None) -> List[float]:
        """
        获取价格序列（用于技术指标计算）
        
        Args:
            pair: 交易对名称
            limit: 返回最近N个价格点
        
        Returns:
            价格列表，按时间从旧到新排序
        """
        history = self.get_history(pair, limit)
        return [point['price'] for point in history]
    
    def get_volume_series(self, pair: str, limit: Optional[int] = None) -> List[float]:
        """
        获取成交量序列
        
        Args:
            pair: 交易对名称
            limit: 返回最近N个数据点
        
        Returns:
            成交量列表，按时间从旧到新排序
        """
        history = self.get_history(pair, limit)
        return [point['volume_24h'] for point in history]
    
    def get_latest_price(self, pair: str) -> Optional[float]:
        """
        获取最新价格
        
        Args:
            pair: 交易对名称
        
        Returns:
            最新价格，如果不存在则返回None
        """
        with self._lock:
            if pair not in self._history or len(self._history[pair]) == 0:
                return None
            return self._history[pair][-1]['price']
    
    def get_data_count(self, pair: str) -> int:
        """
        获取指定交易对的历史数据点数量
        
        Args:
            pair: 交易对名称
        
        Returns:
            数据点数量
        """
        with self._lock:
            if pair not in self._history:
                return 0
            return len(self._history[pair])
    
    def clear(self, pair: Optional[str] = None) -> None:
        """
        清空历史数据
        
        Args:
            pair: 如果指定，只清空该交易对；否则清空所有
        """
        with self._lock:
            if pair:
                if pair in self._history:
                    self._history[pair].clear()
            else:
                self._history.clear()
    
    def get_all_pairs(self) -> List[str]:
        """
        获取所有有历史数据的交易对列表
        
        Returns:
            交易对名称列表
        """
        with self._lock:
            return list(self._history.keys())

