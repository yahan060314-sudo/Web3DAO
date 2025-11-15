"""
技术指标计算模块 - 基于历史价格数据计算各种技术指标

这个模块负责：
1. 计算EMA（指数移动平均）
2. 计算MACD（移动平均收敛散度）
3. 计算RSI（相对强弱指标）
4. 计算其他常用技术指标
"""

from typing import List, Optional, Dict, Any
import math


class TechnicalIndicators:
    """
    技术指标计算器
    所有方法都是静态方法，可以直接调用
    """
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> Optional[List[float]]:
        """
        计算EMA（指数移动平均）
        
        Args:
            prices: 价格序列（按时间从旧到新）
            period: 周期（如12、26、50等）
        
        Returns:
            EMA值列表，如果数据不足则返回None
        """
        if len(prices) < period:
            return None
        
        ema_values = []
        multiplier = 2.0 / (period + 1)
        
        # 第一个EMA值使用SMA（简单移动平均）
        sma = sum(prices[:period]) / period
        ema_values.append(sma)
        
        # 后续EMA值使用公式：EMA = (Price - Previous EMA) * Multiplier + Previous EMA
        for i in range(period, len(prices)):
            ema = (prices[i] - ema_values[-1]) * multiplier + ema_values[-1]
            ema_values.append(ema)
        
        return ema_values
    
    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> Optional[List[float]]:
        """
        计算SMA（简单移动平均）
        
        Args:
            prices: 价格序列
            period: 周期
        
        Returns:
            SMA值列表，如果数据不足则返回None
        """
        if len(prices) < period:
            return None
        
        sma_values = []
        for i in range(period - 1, len(prices)):
            sma = sum(prices[i - period + 1:i + 1]) / period
            sma_values.append(sma)
        
        return sma_values
    
    @staticmethod
    def calculate_macd(prices: List[float], 
                       fast_period: int = 12, 
                       slow_period: int = 26, 
                       signal_period: int = 9) -> Optional[Dict[str, List[float]]]:
        """
        计算MACD（移动平均收敛散度）
        
        Args:
            prices: 价格序列
            fast_period: 快线周期，默认12
            slow_period: 慢线周期，默认26
            signal_period: 信号线周期，默认9
        
        Returns:
            包含MACD线、信号线、柱状图的字典，如果数据不足则返回None
        """
        if len(prices) < slow_period + signal_period:
            return None
        
        # 计算快线和慢线EMA
        fast_ema = TechnicalIndicators.calculate_ema(prices, fast_period)
        slow_ema = TechnicalIndicators.calculate_ema(prices, slow_period)
        
        if not fast_ema or not slow_ema:
            return None
        
        # 对齐长度（慢线较短）
        min_len = min(len(fast_ema), len(slow_ema))
        fast_ema = fast_ema[-min_len:]
        slow_ema = slow_ema[-min_len:]
        
        # MACD线 = 快线EMA - 慢线EMA
        macd_line = [fast_ema[i] - slow_ema[i] for i in range(min_len)]
        
        # 信号线 = MACD线的EMA
        signal_line = TechnicalIndicators.calculate_ema(macd_line, signal_period)
        
        if not signal_line:
            return None
        
        # 对齐长度
        min_len2 = min(len(macd_line), len(signal_line))
        macd_line = macd_line[-min_len2:]
        signal_line = signal_line[-min_len2:]
        
        # 柱状图 = MACD线 - 信号线
        histogram = [macd_line[i] - signal_line[i] for i in range(min_len2)]
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[List[float]]:
        """
        计算RSI（相对强弱指标）
        
        Args:
            prices: 价格序列
            period: 周期，默认14
        
        Returns:
            RSI值列表（0-100），如果数据不足则返回None
        """
        if len(prices) < period + 1:
            return None
        
        rsi_values = []
        gains = []
        losses = []
        
        # 计算价格变化
        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(abs(change))
        
        # 计算初始平均收益和平均损失
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        # 计算第一个RSI值
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))
        rsi_values.append(rsi)
        
        # 计算后续RSI值（使用平滑移动平均）
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = 100.0 - (100.0 / (1.0 + rs))
            rsi_values.append(rsi)
        
        return rsi_values
    
    @staticmethod
    def calculate_bollinger_bands(prices: List[float], 
                                  period: int = 20, 
                                  std_dev: float = 2.0) -> Optional[Dict[str, List[float]]]:
        """
        计算布林带（Bollinger Bands）
        
        Args:
            prices: 价格序列
            period: 周期，默认20
            std_dev: 标准差倍数，默认2.0
        
        Returns:
            包含上轨、中轨（SMA）、下轨的字典，如果数据不足则返回None
        """
        if len(prices) < period:
            return None
        
        sma_values = TechnicalIndicators.calculate_sma(prices, period)
        if not sma_values:
            return None
        
        upper_band = []
        lower_band = []
        
        for i in range(len(sma_values)):
            # 计算标准差
            start_idx = i
            end_idx = start_idx + period
            price_slice = prices[start_idx:end_idx]
            
            mean = sma_values[i]
            variance = sum((p - mean) ** 2 for p in price_slice) / period
            std = math.sqrt(variance)
            
            upper_band.append(mean + std_dev * std)
            lower_band.append(mean - std_dev * std)
        
        return {
            'upper': upper_band,
            'middle': sma_values,
            'lower': lower_band
        }
    
    @staticmethod
    def calculate_all_indicators(prices: List[float]) -> Dict[str, Any]:
        """
        计算所有常用技术指标
        
        Args:
            prices: 价格序列
        
        Returns:
            包含所有技术指标的字典
        """
        indicators = {}
        
        # EMA (多个周期)
        for period in [9, 12, 26, 50, 200]:
            ema = TechnicalIndicators.calculate_ema(prices, period)
            if ema:
                indicators[f'ema_{period}'] = ema[-1] if ema else None
        
        # SMA (多个周期)
        for period in [20, 50, 200]:
            sma = TechnicalIndicators.calculate_sma(prices, period)
            if sma:
                indicators[f'sma_{period}'] = sma[-1] if sma else None
        
        # MACD
        macd = TechnicalIndicators.calculate_macd(prices)
        if macd:
            indicators['macd'] = macd['macd'][-1] if macd['macd'] else None
            indicators['macd_signal'] = macd['signal'][-1] if macd['signal'] else None
            indicators['macd_histogram'] = macd['histogram'][-1] if macd['histogram'] else None
        
        # RSI
        rsi = TechnicalIndicators.calculate_rsi(prices)
        if rsi:
            indicators['rsi'] = rsi[-1] if rsi else None
        
        # 布林带
        bb = TechnicalIndicators.calculate_bollinger_bands(prices)
        if bb:
            indicators['bb_upper'] = bb['upper'][-1] if bb['upper'] else None
            indicators['bb_middle'] = bb['middle'][-1] if bb['middle'] else None
            indicators['bb_lower'] = bb['lower'][-1] if bb['lower'] else None
        
        return indicators

