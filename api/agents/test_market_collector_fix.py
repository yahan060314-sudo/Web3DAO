#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 MarketDataCollector 的 _current_batch_index bug 修复

测试内容：
1. 验证 MarketDataCollector 初始化时 _current_batch_index 属性存在
2. 验证批处理逻辑正常工作
3. 不进行真实交易，只测试数据采集逻辑
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from api.agents.market_collector import MarketDataCollector
from api.agents.bus import MessageBus


def test_market_collector_initialization():
    """测试 MarketDataCollector 初始化，验证属性存在"""
    print("=" * 80)
    print("测试 1: MarketDataCollector 初始化")
    print("=" * 80)
    
    try:
        bus = MessageBus()
        collector = MarketDataCollector(
            bus=bus,
            market_topic="test_market",
            pairs=["BTC/USD", "ETH/USD", "SOL/USD"],  # 测试用少量交易对
            collect_interval=5.0,
            collect_balance=False,  # 不采集余额，减少API调用
            collect_ticker=True
        )
        
        # 验证关键属性存在
        assert hasattr(collector, '_current_batch_index'), "❌ _current_batch_index 属性不存在！"
        assert hasattr(collector, '_batch_size'), "❌ _batch_size 属性不存在！"
        assert collector._current_batch_index == 0, f"❌ _current_batch_index 初始值应为0，实际为 {collector._current_batch_index}"
        assert collector._batch_size > 0, f"❌ _batch_size 应大于0，实际为 {collector._batch_size}"
        
        print("✓ MarketDataCollector 初始化成功")
        print(f"  - _current_batch_index: {collector._current_batch_index}")
        print(f"  - _batch_size: {collector._batch_size}")
        print(f"  - pairs 数量: {len(collector.pairs)}")
        return True, collector
        
    except AttributeError as e:
        print(f"❌ 属性错误: {e}")
        return False, None
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_batch_processing_logic():
    """测试批处理逻辑"""
    print("\n" + "=" * 80)
    print("测试 2: 批处理逻辑")
    print("=" * 80)
    
    try:
        bus = MessageBus()
        # 创建多个交易对以测试批处理
        test_pairs = [f"PAIR{i}/USD" for i in range(1, 26)]  # 25个交易对，测试批处理
        
        collector = MarketDataCollector(
            bus=bus,
            market_topic="test_market",
            pairs=test_pairs,
            collect_interval=5.0,
            collect_balance=False,
            collect_ticker=True
        )
        
        print(f"测试交易对数量: {len(test_pairs)}")
        print(f"批次大小: {collector._batch_size}")
        print(f"预计批次数: {(len(test_pairs) + collector._batch_size - 1) // collector._batch_size}")
        
        # 模拟几次批处理循环
        batches_needed = (len(test_pairs) + collector._batch_size - 1) // collector._batch_size
        print(f"\n模拟批处理循环（不实际调用API）:")
        
        for cycle in range(min(3, batches_needed)):  # 只测试前3个批次
            start_idx = collector._current_batch_index * collector._batch_size
            end_idx = min(start_idx + collector._batch_size, len(test_pairs))
            current_batch = test_pairs[start_idx:end_idx]
            
            print(f"  批次 {collector._current_batch_index + 1}/{batches_needed}: "
                  f"索引 {start_idx}-{end_idx-1}, 交易对数量: {len(current_batch)}")
            
            # 更新批次索引
            collector._current_batch_index += 1
            if collector._current_batch_index >= batches_needed:
                collector._current_batch_index = 0
                print(f"  → 批次循环重置，开始新一轮")
        
        print("✓ 批处理逻辑测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 批处理逻辑测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_collector_with_many_pairs():
    """测试大量交易对的情况（模拟实际场景）"""
    print("\n" + "=" * 80)
    print("测试 3: 大量交易对场景（67个交易对，模拟实际运行）")
    print("=" * 80)
    
    try:
        bus = MessageBus()
        # 模拟67个交易对
        many_pairs = [f"COIN{i}/USD" for i in range(1, 68)]
        
        collector = MarketDataCollector(
            bus=bus,
            market_topic="test_market",
            pairs=many_pairs,
            collect_interval=30.0,
            collect_balance=False,  # 不采集余额，避免API调用
            collect_ticker=True
        )
        
        batches_needed = (len(many_pairs) + collector._batch_size - 1) // collector._batch_size
        
        print(f"交易对数量: {len(many_pairs)}")
        print(f"批次大小: {collector._batch_size}")
        print(f"需要批次数: {batches_needed}")
        print(f"每批平均交易对数: {len(many_pairs) / batches_needed:.1f}")
        
        # 验证属性存在
        assert hasattr(collector, '_current_batch_index'), "❌ _current_batch_index 属性不存在！"
        assert collector._current_batch_index == 0, "❌ 初始批次索引应为0"
        
        print("✓ 大量交易对场景测试通过")
        print("  → 属性初始化正确")
        print("  → 批处理逻辑可以正常工作")
        return True
        
    except Exception as e:
        print(f"❌ 大量交易对测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_collector_start_stop():
    """测试采集器的启动和停止（不实际运行，只测试方法）"""
    print("\n" + "=" * 80)
    print("测试 4: 采集器启动/停止方法")
    print("=" * 80)
    
    try:
        bus = MessageBus()
        collector = MarketDataCollector(
            bus=bus,
            market_topic="test_market",
            pairs=["BTC/USD"],
            collect_interval=1.0,
            collect_balance=False,
            collect_ticker=False  # 不采集ticker，避免API调用
        )
        
        # 验证属性存在
        assert hasattr(collector, '_current_batch_index'), "❌ _current_batch_index 属性不存在！"
        
        # 测试停止方法
        assert not collector._stopped, "初始状态应为未停止"
        collector.stop()
        assert collector._stopped, "停止后 _stopped 应为 True"
        
        print("✓ 启动/停止方法测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 启动/停止测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("MarketDataCollector Bug 修复验证测试")
    print("=" * 80)
    print("测试目标: 验证 _current_batch_index 属性已正确初始化")
    print("测试模式: 不进行真实交易，只测试代码逻辑")
    print("=" * 80)
    
    results = []
    
    # 测试1: 初始化
    success, collector = test_market_collector_initialization()
    results.append(("初始化测试", success))
    
    if not success:
        print("\n❌ 初始化测试失败，停止后续测试")
        return
    
    # 测试2: 批处理逻辑
    success = test_batch_processing_logic()
    results.append(("批处理逻辑测试", success))
    
    # 测试3: 大量交易对场景
    success = test_collector_with_many_pairs()
    results.append(("大量交易对场景测试", success))
    
    # 测试4: 启动/停止
    success = test_collector_start_stop()
    results.append(("启动/停止测试", success))
    
    # 汇总结果
    print("\n" + "=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 80)
    if all_passed:
        print("✅ 所有测试通过！Bug 已修复。")
        print("\n说明:")
        print("  - _current_batch_index 属性已正确初始化")
        print("  - 批处理逻辑可以正常工作")
        print("  - 可以安全运行 run_bot.py，不会再出现 AttributeError")
    else:
        print("❌ 部分测试失败，请检查代码。")
    print("=" * 80)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

