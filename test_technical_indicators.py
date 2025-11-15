#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试技术指标计算功能
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api.agents.history_storage import HistoryStorage
from api.agents.technical_indicators import TechnicalIndicators
from api.agents.data_formatter import DataFormatter

def test_technical_indicators():
    """测试技术指标计算"""
    print("=" * 60)
    print("技术指标计算测试")
    print("=" * 60)
    
    # 1. 创建历史数据存储
    storage = HistoryStorage(max_history_size=1000)
    
    # 2. 模拟添加一些历史价格数据（模拟价格上涨趋势）
    print("\n[1] 添加模拟历史数据...")
    base_price = 100.0
    for i in range(50):  # 添加50个数据点
        price = base_price + i * 0.5 + (i % 3) * 0.2  # 模拟价格波动
        ticker_data = {
            'price': price,
            'volume_24h': 1000000.0 + i * 10000,
            'change_24h': (price - base_price) / base_price * 100,
            'high_24h': price * 1.02,
            'low_24h': price * 0.98
        }
        storage.add_ticker("BTC/USD", ticker_data)
    
    print(f"✓ 已添加 {storage.get_data_count('BTC/USD')} 个数据点")
    
    # 3. 获取价格序列并计算技术指标
    print("\n[2] 计算技术指标...")
    price_series = storage.get_price_series("BTC/USD")
    print(f"✓ 价格序列长度: {len(price_series)}")
    print(f"  最新价格: ${price_series[-1]:.2f}")
    print(f"  最早价格: ${price_series[0]:.2f}")
    
    # 计算所有指标
    indicators = TechnicalIndicators.calculate_all_indicators(price_series)
    
    print("\n[3] 技术指标结果:")
    print(f"  RSI(14): {indicators.get('rsi', 'N/A')}")
    print(f"  EMA(9): ${indicators.get('ema_9', 'N/A')}")
    print(f"  EMA(26): ${indicators.get('ema_26', 'N/A')}")
    print(f"  EMA(50): ${indicators.get('ema_50', 'N/A')}")
    print(f"  MACD: {indicators.get('macd', 'N/A')}")
    print(f"  MACD Signal: {indicators.get('macd_signal', 'N/A')}")
    print(f"  MACD Histogram: {indicators.get('macd_histogram', 'N/A')}")
    print(f"  Bollinger Bands Upper: ${indicators.get('bb_upper', 'N/A')}")
    print(f"  Bollinger Bands Middle: ${indicators.get('bb_middle', 'N/A')}")
    print(f"  Bollinger Bands Lower: ${indicators.get('bb_lower', 'N/A')}")
    
    # 4. 测试在market snapshot中包含技术指标
    print("\n[4] 测试market snapshot包含技术指标...")
    formatter = DataFormatter()
    
    # 创建包含技术指标的ticker数据
    ticker_data = {
        'pair': 'BTC/USD',
        'price': price_series[-1],
        'volume_24h': 1000000.0,
        'change_24h': 2.5,
        'high_24h': price_series[-1] * 1.02,
        'low_24h': price_series[-1] * 0.98,
        'indicators': indicators
    }
    
    snapshot = formatter.create_market_snapshot(
        tickers={'BTC/USD': ticker_data},
        history_storage=storage
    )
    
    # 格式化并显示
    formatted_text = formatter.format_for_llm(snapshot)
    print("\n[5] 格式化后的市场数据（包含技术指标）:")
    print("-" * 60)
    print(formatted_text)
    print("-" * 60)
    
    print("\n✓ 测试完成！")

if __name__ == "__main__":
    test_technical_indicators()

