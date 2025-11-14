"""
频率限制器 - 用于限制API调用和决策生成的频率

根据要求：
- API调用：每分钟最多5次（12秒间隔）
- 决策生成：每分钟最多1次（60秒间隔）
"""

import time
from typing import Optional
from collections import deque


class RateLimiter:
    """
    频率限制器：使用滑动窗口算法限制调用频率
    """
    
    def __init__(self, max_calls: int, time_window: float):
        """
        初始化频率限制器
        
        Args:
            max_calls: 时间窗口内允许的最大调用次数
            time_window: 时间窗口（秒）
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.call_times: deque = deque()
        self._lock = False  # 简单的锁，防止并发问题
    
    def can_call(self) -> bool:
        """
        检查是否可以调用
        
        Returns:
            True如果可以调用，False如果超过限制
        """
        now = time.time()
        
        # 移除时间窗口外的调用记录
        while self.call_times and (now - self.call_times[0]) > self.time_window:
            self.call_times.popleft()
        
        # 检查是否超过限制
        if len(self.call_times) >= self.max_calls:
            return False
        
        return True
    
    def record_call(self) -> None:
        """
        记录一次调用
        """
        now = time.time()
        self.call_times.append(now)
        
        # 清理过期记录
        while self.call_times and (now - self.call_times[0]) > self.time_window:
            self.call_times.popleft()
    
    def wait_time(self) -> float:
        """
        获取需要等待的时间（秒）
        
        Returns:
            需要等待的秒数，如果不需要等待则返回0
        """
        if self.can_call():
            return 0.0
        
        now = time.time()
        # 计算最早可以调用时间
        if self.call_times:
            earliest_call_time = self.call_times[0]
            wait_until = earliest_call_time + self.time_window
            return max(0.0, wait_until - now)
        
        return 0.0
    
    def reset(self) -> None:
        """重置限制器"""
        self.call_times.clear()


# 预定义的频率限制器
# 将API调用限制从每分钟5次降为每分钟3次，以进一步降低对API的压力
API_RATE_LIMITER = RateLimiter(max_calls=3, time_window=60.0)  # 每分钟最多3次
DECISION_RATE_LIMITER = RateLimiter(max_calls=1, time_window=60.0)  # 每个Agent每分钟最多1次（已废弃，保留兼容性）
# 全局决策频率限制：整个bot每分钟最多2次（允许两个Agent都能做决策）
GLOBAL_DECISION_RATE_LIMITER = RateLimiter(max_calls=2, time_window=60.0)





