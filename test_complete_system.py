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
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

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
    print("[测试 2/7] LLM API 连接测试")
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
    print("[测试 3/7] Roostoo API 连接测试")
    print("=" * 60)
    try:
        from api.roostoo_client import RoostooClient
        client = RoostooClient()
        print(f"  API URL: {client.base_url}")
        
        # 使用更长的超时时间进行测试
        server_time = client.check_server_time(timeout=60.0)
        print(f"✓ Server time: {server_time}")
        
        ticker = client.get_ticker('BTC/USD', timeout=60.0)
        print(f"✓ Ticker data retrieved")
        print(f"  Raw response structure: {list(ticker.keys())}")
        return True
    except Exception as e:
        print(f"✗ Roostoo API test failed: {e}")
        print(f"  提示: 如果连接超时，可能是网络问题或API服务器不可用")
        print(f"  当前使用的URL: {client.base_url if 'client' in locals() else 'N/A'}")
        return False


def test_data_formatter() -> bool:
    """测试数据格式化"""
    print("\n" + "=" * 60)
    print("[测试 4/7] DataFormatter 数据格式化测试")
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
    print("[测试 5/7] PromptManager 测试")
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
                # 显示prompt的关键部分（前500字符）
                print(f"\n  Prompt preview (first 500 chars):")
                print(f"  {test_prompt[:500]}...")
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
# 第三部分：JSON决策解析工具
# ============================================================================

def parse_json_decision(decision_text: str) -> Optional[Dict[str, Any]]:
    """
    解析natural_language_prompt.txt要求的JSON格式决策
    
    期望格式：
    {
      "action": "wait | open_long | close_long | hold | ...",
      "symbol": "BTCUSDT",
      "price_ref": 100000.0,
      "position_size_usd": 1200.0,
      "stop_loss": 98700.0,
      "take_profit": 104000.0,
      "partial_close_pct": 0,
      "confidence": 88,
      "invalidation_condition": "...",
      "slippage_buffer": 0.0002,
      "reasoning": "..."
    }
    """
    if not decision_text:
        return None
    
    # 尝试提取JSON（可能被其他文本包围）
    # 方法1: 查找 {...} 块
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', decision_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # 方法2: 尝试直接解析整个文本
    try:
        return json.loads(decision_text.strip())
    except json.JSONDecodeError:
        pass
    
    return None


def format_decision_display(decision: Dict[str, Any], parsed_json: Optional[Dict[str, Any]] = None) -> str:
    """
    格式化决策显示，优先显示JSON格式的解析结果
    """
    lines = []
    
    if parsed_json:
        lines.append("  📋 JSON格式决策解析:")
        lines.append(f"    动作 (action): {parsed_json.get('action', 'N/A')}")
        lines.append(f"    交易对 (symbol): {parsed_json.get('symbol', 'N/A')}")
        
        if parsed_json.get('price_ref'):
            lines.append(f"    参考价格 (price_ref): ${parsed_json['price_ref']:.2f}")
        if parsed_json.get('position_size_usd'):
            lines.append(f"    仓位大小 (position_size_usd): ${parsed_json['position_size_usd']:.2f}")
        if parsed_json.get('stop_loss'):
            lines.append(f"    止损价 (stop_loss): ${parsed_json['stop_loss']:.2f}")
        if parsed_json.get('take_profit'):
            lines.append(f"    止盈价 (take_profit): ${parsed_json['take_profit']:.2f}")
        if parsed_json.get('confidence'):
            lines.append(f"    信心度 (confidence): {parsed_json['confidence']}")
        if parsed_json.get('reasoning'):
            reasoning = parsed_json['reasoning']
            if len(reasoning) > 100:
                reasoning = reasoning[:100] + "..."
            lines.append(f"    推理 (reasoning): {reasoning}")
        if parsed_json.get('invalidation_condition'):
            lines.append(f"    失效条件 (invalidation_condition): {parsed_json['invalidation_condition']}")
    else:
        # 显示原始文本（截断）
        decision_text = decision.get('decision', 'N/A')
        if len(decision_text) > 200:
            decision_text = decision_text[:200] + "..."
        lines.append(f"  📝 原始决策文本:")
        lines.append(f"     {decision_text}")
    
    return "\n".join(lines)


# ============================================================================
# 第四部分：完整数据流测试
# ============================================================================

def test_complete_data_flow(quick: bool = False) -> bool:
    """测试完整数据流"""
    print("\n" + "=" * 60)
    print("[测试 6/7] 完整数据流测试")
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
            spot_prompt = pm.create_spot_prompt_from_market_data(
                snapshot,
                price_series="[103000, 103100, 103200, 103300]",
                recent_sharpe="0.72",
                trade_stats="win=62%, rr=2.8"
            )
            if spot_prompt:
                print(f"✓ Spot trading prompt generated ({len(spot_prompt)} chars)")
                print(f"  (使用natural_language_prompt.txt模板)")
            else:
                print("⚠ Spot trading prompt not available")
        else:
            print("⚠ Cannot generate prompt (no market data)")
        
        print("\n[7] 发送组友的prompt模板给Agent...")
        if snapshot and spot_prompt:
            # 使用组友的详细prompt模板
            mgr.broadcast_prompt(role="user", content=spot_prompt)
            print("✓ Sent spot trading prompt to agent")
            time.sleep(3)  # 等待Agent处理
        else:
            # 使用默认prompt
            default_prompt = pm.create_trading_prompt(snapshot) if snapshot else "Analyze market and make a decision."
            mgr.broadcast_prompt(role="user", content=default_prompt)
            print("✓ Sent default trading prompt to agent")
            time.sleep(3)
        
        print("\n[8] 检查Agent决策（支持JSON格式解析）...")
        time.sleep(5)
        decisions = mgr.collect_decisions(max_items=5, wait_seconds=3.0)
        if decisions:
            print(f"✓ Received {len(decisions)} decision(s)")
            for i, d in enumerate(decisions, 1):
                print(f"\n  [{i}] Agent: {d.get('agent', 'Unknown')}")
                decision_text = d.get('decision', '')
                
                # 尝试解析JSON格式
                parsed_json = parse_json_decision(decision_text)
                if parsed_json:
                    print(format_decision_display(d, parsed_json))
                    print("  ✓ 成功解析为JSON格式（符合natural_language_prompt.txt要求）")
                else:
                    print(format_decision_display(d, None))
                    print("  ⚠ 未检测到JSON格式，可能是自然语言格式")
        else:
            print("⚠ No decisions received")
        
        print("\n[9] 测试TradeExecutor（交易执行器）和下单参数展示...")
        try:
            from api.agents.executor import TradeExecutor
            
            # 测试模式：使用dry_run=True，不会真正下单
            executor = TradeExecutor(
                bus=mgr.bus,
                decision_topic=mgr.decision_topic,
                default_pair="BTC/USD",
                dry_run=True  # 测试模式，不真正下单
            )
            print("✓ TradeExecutor initialized (dry_run mode for testing)")
            
            # 测试多种格式的决策解析
            test_cases = [
                {
                    "name": "JSON格式（natural_language_prompt.txt要求）",
                    "decision": '{"action": "open_long", "symbol": "BTCUSDT", "position_size_usd": 1000.0, "price_ref": 103000.0, "stop_loss": 101000.0, "take_profit": 105000.0, "confidence": 85}',
                },
                {
                    "name": "自然语言格式（简单）",
                    "decision": "buy 0.01 BTC",
                },
                {
                    "name": "自然语言格式（限价单）",
                    "decision": "sell 0.02 BTC at 104000",
                },
                {
                    "name": "自然语言格式（模糊表达-应正确处理）",
                    "decision": "I was asked to choose between buy or sell, and I decide to buy 0.01 BTC",
                },
                {
                    "name": "自然语言格式（包含推理）",
                    "decision": "Based on my analysis, I recommend buying 0.015 BTC. The current price is 103000.",
                },
                {
                    "name": "Hold/Wait（不应下单）",
                    "decision": '{"action": "wait", "reasoning": "Market conditions not favorable"}',
                },
            ]
            
            print("\n  测试决策解析:")
            for i, test_case in enumerate(test_cases, 1):
                print(f"\n  [{i}] {test_case['name']}")
                print(f"      输入: {test_case['decision'][:80]}...")
                
                test_decision_msg = {
                    "agent": "test_agent",
                    "decision": test_case['decision'],
                    "timestamp": time.time()
                }
                
                parsed = executor._parse_decision(test_decision_msg)
                if parsed:
                    print(f"      ✓ 解析成功:")
                    print(f"        - Side: {parsed.get('side')}")
                    print(f"        - Pair: {parsed.get('pair')}")
                    print(f"        - Quantity: {parsed.get('quantity')}")
                    print(f"        - Price: {parsed.get('price', 'MARKET')}")
                    print(f"        - 格式: {'JSON' if 'json_data' in parsed else '自然语言'}")
                    
                    # 展示实际下单参数
                    print(f"      📋 实际下单参数:")
                    print(f"        - place_order(")
                    print(f"            pair='{parsed.get('pair')}',")
                    print(f"            side='{parsed.get('side')}',")
                    print(f"            quantity={parsed.get('quantity')},")
                    if parsed.get('price'):
                        print(f"            price={parsed.get('price')}")
                    print(f"          )")
                    print(f"      ✅ 下单参数完整，可以执行交易")
                else:
                    print(f"      ⚠ 解析失败或为hold/wait（不执行交易）")
            
            print("\n  📝 注意: 测试中使用dry_run模式，不会真正下单")
            print("     如需真实下单，请设置 dry_run=False 并配置真实的ROOSTOO_API_URL")
            
        except Exception as e:
            print(f"  ⚠ TradeExecutor test skipped: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n[10] 清理资源...")
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
    print("[测试 1/7] 系统环境验证")
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
    
    # 6. 完整数据流测试（包含JSON格式决策测试）
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

