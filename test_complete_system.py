#!/usr/bin/env python3
"""
完整系统测试脚本 - 整合所有测试功能

这个脚本整合了所有测试功能：
1. 系统验证
2. LLM连接测试
3. Roostoo API连接测试
4. 数据格式化测试
5. Prompt管理器测试
6. 完整数据流测试

运行方式：
    python test_complete_system.py [--quick] [--full]
    
选项：
    --quick: 快速测试（约30秒）
    --full: 完整测试（约2分钟，包含完整集成测试）
    默认: 标准测试（约1分钟）
"""

import sys
import os
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple

# ============================================================================
# 第一部分：系统验证
# ============================================================================

def verify_system() -> Tuple[bool, List[str], List[str]]:
    """验证系统环境"""
    checks = []
    errors = []
    
    # 1. Python版本
    if sys.version_info >= (3, 11):
        checks.append(f"✓ Python version: {sys.version.split()[0]}")
    else:
        errors.append("✗ Python version too old (need 3.11+)")
    
    # 2. 依赖检查
    try:
        import requests
        checks.append("✓ requests installed")
    except ImportError:
        errors.append("✗ requests not installed")
    
    try:
        import dotenv
        checks.append("✓ python-dotenv installed")
    except ImportError:
        errors.append("✗ python-dotenv not installed")
    
    # 3. 配置文件
    env_file = Path(".env")
    if env_file.exists():
        checks.append("✓ .env file exists")
        from dotenv import load_dotenv
        load_dotenv()
        if os.getenv("DEEPSEEK_API_KEY") and "your-actual" not in os.getenv("DEEPSEEK_API_KEY", ""):
            checks.append("✓ DEEPSEEK_API_KEY configured")
        else:
            errors.append("✗ DEEPSEEK_API_KEY not set or is placeholder")
        
        if os.getenv("ROOSTOO_API_KEY") and "your_roostoo" not in os.getenv("ROOSTOO_API_KEY", ""):
            checks.append("✓ ROOSTOO_API_KEY configured")
        else:
            errors.append("✗ ROOSTOO_API_KEY not set or is placeholder")
    else:
        errors.append("✗ .env file not found")
    
    # 4. 模块导入
    try:
        from api.llm_clients.factory import get_llm_client
        checks.append("✓ LLM clients importable")
    except Exception as e:
        errors.append(f"✗ LLM clients import error: {e}")
    
    try:
        from api.roostoo_client import RoostooClient
        checks.append("✓ Roostoo client importable")
    except Exception as e:
        errors.append(f"✗ Roostoo client import error: {e}")
    
    try:
        from api.agents.manager import AgentManager
        from api.agents.market_collector import MarketDataCollector
        from api.agents.prompt_manager import PromptManager
        checks.append("✓ Agent modules importable")
    except Exception as e:
        errors.append(f"✗ Agent modules import error: {e}")
    
    return len(errors) == 0, checks, errors


# ============================================================================
# 第二部分：组件测试
# ============================================================================

def test_llm_connection() -> bool:
    """测试LLM连接"""
    print("\n" + "=" * 60)
    print("[测试 2/6] LLM API 连接测试")
    print("=" * 60)
    try:
        from api.llm_clients.example_usage import run_demo
        run_demo()
        print("✓ LLM connection test passed")
        return True
    except Exception as e:
        print(f"✗ LLM connection test failed: {e}")
        return False


def test_roostoo_connection() -> bool:
    """测试Roostoo API连接"""
    print("\n" + "=" * 60)
    print("[测试 3/6] Roostoo API 连接测试")
    print("=" * 60)
    try:
        from api.roostoo_client import RoostooClient
        client = RoostooClient()
        server_time = client.check_server_time()
        print(f"✓ Server time: {server_time}")
        
        ticker = client.get_ticker('BTC/USD')
        print(f"✓ Ticker data retrieved")
        print(f"  Raw response structure: {list(ticker.keys())}")
        return True
    except Exception as e:
        print(f"✗ Roostoo API test failed: {e}")
        return False


def test_data_formatter() -> bool:
    """测试数据格式化"""
    print("\n" + "=" * 60)
    print("[测试 4/6] DataFormatter 数据格式化测试")
    print("=" * 60)
    try:
        from api.agents.data_formatter import DataFormatter
        
        formatter = DataFormatter()
        
        # 测试真实的Roostoo数据格式
        roostoo_ticker = {
            'Success': True,
            'ErrMsg': '',
            'ServerTime': 1762565986151,
            'Data': {
                'BTC/USD': {
                    'MaxBid': 103149.87,
                    'MinAsk': 103149.88,
                    'LastPrice': 103149.88,
                    'Change': 0.0189,
                    'CoinTradeValue': 31670.99277,
                    'UnitTradeValue': 3213826873.114794
                }
            }
        }
        
        formatted = formatter.format_ticker(roostoo_ticker, "BTC/USD")
        print(f"✓ Ticker formatted successfully")
        print(f"  Pair: {formatted.get('pair')}")
        print(f"  Price: ${formatted.get('price', 'N/A')}")
        print(f"  Change 24h: {formatted.get('change_24h', 'N/A')}%")
        
        if formatted.get('price') is None:
            print("  ⚠ Warning: Price not extracted (check data format)")
            return False
        
        # 测试balance格式
        roostoo_balance = {
            'Success': True,
            'ErrMsg': '',
            'SpotWallet': {
                'USD': {'Free': 50000, 'Lock': 0}
            },
            'MarginWallet': {}
        }
        
        formatted_balance = formatter.format_balance(roostoo_balance)
        print(f"✓ Balance formatted successfully")
        print(f"  Total Balance: ${formatted_balance.get('total_balance', 'N/A')}")
        print(f"  Available: ${formatted_balance.get('available_balance', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"✗ DataFormatter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prompt_manager() -> bool:
    """测试Prompt管理器"""
    print("\n" + "=" * 60)
    print("[测试 5/6] PromptManager 测试")
    print("=" * 60)
    try:
        from api.agents.prompt_manager import PromptManager
        
        pm = PromptManager()
        print("✓ PromptManager initialized")
        
        # 测试系统prompt
        system_prompt = pm.get_system_prompt('TestAgent', risk_level='moderate')
        print(f"✓ System prompt generated ({len(system_prompt)} chars)")
        
        # 检查组友的模板
        if hasattr(pm, 'spot_trading_template') and pm.spot_trading_template:
            print("✓ Spot trading template loaded")
            
            # 测试模板格式化
            test_prompt = pm.get_spot_trading_prompt(
                date="2025-01-07",
                account_equity="10000",
                available_cash="8000",
                positions="BTC: 0.1",
                price_series="[103000, 103100, 103200]",
                recent_sharpe="0.72"
            )
            if test_prompt:
                print(f"✓ Spot trading prompt generated ({len(test_prompt)} chars)")
            else:
                print("⚠ Spot trading prompt generation failed")
        else:
            print("⚠ Spot trading template not loaded (optional)")
        
        return True
    except Exception as e:
        print(f"✗ PromptManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# 第三部分：完整数据流测试
# ============================================================================

def test_complete_data_flow(quick: bool = False) -> bool:
    """测试完整数据流"""
    print("\n" + "=" * 60)
    print("[测试 6/6] 完整数据流测试")
    print("=" * 60)
    
    try:
        from api.agents.manager import AgentManager
        from api.agents.market_collector import MarketDataCollector
        from api.agents.prompt_manager import PromptManager
        
        print("\n[1] 初始化组件...")
        mgr = AgentManager()
        pm = PromptManager()
        print("✓ Components initialized")
        
        print("\n[2] 创建并启动 Agent...")
        system_prompt = pm.get_system_prompt("TestAgent", risk_level="moderate")
        mgr.add_agent(name="test_agent", system_prompt=system_prompt)
        mgr.start()
        print("✓ Agent started")
        
        print("\n[3] 启动市场数据采集器...")
        collector = MarketDataCollector(
            bus=mgr.bus,
            market_topic=mgr.market_topic,
            pairs=["BTC/USD"],
            collect_interval=3.0,
            collect_balance=True,
            collect_ticker=True
        )
        collector.start()
        print("✓ Data collector started")
        
        # 等待数据采集
        wait_time = 5 if quick else 10
        print(f"\n[4] 等待市场数据采集 ({wait_time}秒)...")
        time.sleep(wait_time)
        
        print("\n[5] 检查采集到的数据...")
        snapshot = collector.get_latest_snapshot()
        if snapshot:
            print("✓ Market snapshot created")
            ticker = snapshot.get("ticker")
            balance = snapshot.get("balance")
            
            if ticker:
                price = ticker.get("price")
                if price:
                    print(f"  ✓ Ticker data: Price = ${price:.2f}")
                else:
                    print(f"  ⚠ Ticker data: Price not extracted (check format)")
            else:
                print(f"  ⚠ No ticker data in snapshot")
            
            if balance:
                total = balance.get("total_balance")
                if total:
                    print(f"  ✓ Balance data: Total = ${total:.2f}")
                else:
                    print(f"  ⚠ Balance data: Total not extracted (check format)")
            else:
                print(f"  ⚠ No balance data in snapshot")
        else:
            print("⚠ No market snapshot yet")
        
        print("\n[6] 测试Prompt生成...")
        if snapshot:
            # 测试默认prompt
            prompt = pm.create_trading_prompt(snapshot)
            print(f"✓ Trading prompt generated ({len(prompt)} chars)")
            
            # 测试组友的模板
            spot_prompt = pm.create_spot_prompt_from_market_data(snapshot)
            if spot_prompt:
                print(f"✓ Spot trading prompt generated ({len(spot_prompt)} chars)")
            else:
                print("⚠ Spot trading prompt not available")
        else:
            print("⚠ Cannot generate prompt (no market data)")
        
        print("\n[7] 检查Agent决策...")
        time.sleep(5)
        decisions = mgr.collect_decisions(max_items=3, wait_seconds=2.0)
        if decisions:
            print(f"✓ Received {len(decisions)} decision(s)")
            for i, d in enumerate(decisions, 1):
                decision_text = d.get('decision', 'N/A')
                print(f"  {i}. Agent: {d.get('agent')}")
                print(f"     Decision: {decision_text[:100]}...")
        else:
            print("⚠ No decisions received")
        
        print("\n[8] 清理资源...")
        collector.stop()
        collector.join(timeout=2)
        mgr.stop()
        print("✓ Cleanup complete")
        
        return True
    except Exception as e:
        print(f"✗ Data flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# 主函数
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Complete System Test")
    parser.add_argument('--quick', action='store_true', help='Quick test (30 seconds)')
    parser.add_argument('--full', action='store_true', help='Full test (2 minutes)')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Web3DAO Complete System Test")
    print("=" * 60)
    
    results = []
    
    # 1. 系统验证
    print("\n" + "=" * 60)
    print("[测试 1/6] 系统环境验证")
    print("=" * 60)
    success, checks, errors = verify_system()
    for check in checks:
        print(f"  {check}")
    if errors:
        print("\nErrors/Warnings:")
        for error in errors:
            print(f"  {error}")
    results.append(("System Verification", success))
    
    if not success:
        print("\n✗ System verification failed. Please fix errors before continuing.")
        return 1
    
    # 2-5. 组件测试
    results.append(("LLM Connection", test_llm_connection()))
    results.append(("Roostoo Connection", test_roostoo_connection()))
    results.append(("Data Formatter", test_data_formatter()))
    results.append(("Prompt Manager", test_prompt_manager()))
    
    # 6. 完整数据流测试
    results.append(("Complete Data Flow", test_complete_data_flow(quick=args.quick)))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    print("=" * 60)
    
    if passed == total:
        print("✓✓✓ 所有测试通过！ ✓✓✓")
        return 0
    else:
        print("⚠ 部分测试失败，请检查上述错误信息")
        return 1


if __name__ == "__main__":
    sys.exit(main())

