#!/usr/bin/env python3
"""
生产环境运行脚本 - 真实交易，会上传到leaderboard

这个脚本会：
1. 验证所有必要的配置
2. 从API获取初始本金并均分给两个Agent
3. 运行真实交易系统（dry_run=False）
4. 显示实时交易信息和统计
5. 运行至少30分钟以便在leaderboard上看到结果

运行方式：
    python run_production.py [运行时长（分钟），默认30]
"""
import os
import sys
import time
import signal
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from api.agents.manager import AgentManager
from api.agents.executor import TradeExecutor
from api.agents.market_collector import MarketDataCollector
from api.agents.prompt_manager import PromptManager
from api.agents.capital_manager import CapitalManager
from api.roostoo_client import RoostooClient
from api.llm_clients.factory import get_llm_client


# 全局变量用于优雅关闭
shutdown_requested = False
start_time = None
stats = {
    "total_decisions": 0,
    "total_orders": 0,
    "successful_orders": 0,
    "failed_orders": 0,
    "agents": {}
}


def signal_handler(sig, frame):
    """处理Ctrl+C信号，优雅关闭"""
    global shutdown_requested
    print("\n\n" + "=" * 80)
    print("收到停止信号，正在优雅关闭...")
    print("=" * 80)
    shutdown_requested = True


def verify_configuration() -> bool:
    """验证所有必要的配置"""
    print("=" * 80)
    print("配置验证")
    print("=" * 80)
    print()
    
    errors = []
    warnings = []
    
    # 检查Roostoo API配置
    api_key = os.getenv("ROOSTOO_API_KEY")
    secret_key = os.getenv("ROOSTOO_SECRET_KEY")
    api_url = os.getenv("ROOSTOO_API_URL")
    
    if not api_key:
        errors.append("❌ ROOSTOO_API_KEY未在.env中设置")
    else:
        print(f"✓ ROOSTOO_API_KEY已配置: {api_key[:10]}...{api_key[-10:]}")
    
    if not secret_key:
        errors.append("❌ ROOSTOO_SECRET_KEY未在.env中设置")
    else:
        print(f"✓ ROOSTOO_SECRET_KEY已配置: {secret_key[:10]}...{secret_key[-10:]}")
    
    if not api_url:
        errors.append("❌ ROOSTOO_API_URL未在.env中设置")
    else:
        print(f"✓ ROOSTOO_API_URL已配置: {api_url}")
    
    # 检查LLM配置
    llm_provider = os.getenv("LLM_PROVIDER", "deepseek")
    print(f"✓ LLM_PROVIDER: {llm_provider}")
    
    if llm_provider == "deepseek":
        llm_key = os.getenv("DEEPSEEK_API_KEY")
        if not llm_key:
            errors.append("❌ DEEPSEEK_API_KEY未在.env中设置")
        else:
            print(f"✓ DEEPSEEK_API_KEY已配置: {llm_key[:10]}...")
    elif llm_provider == "qwen":
        llm_key = os.getenv("QWEN_API_KEY")
        if not llm_key:
            errors.append("❌ QWEN_API_KEY未在.env中设置")
        else:
            print(f"✓ QWEN_API_KEY已配置: {llm_key[:10]}...")
    elif llm_provider == "minimax":
        llm_key = os.getenv("MINIMAX_API_KEY")
        if not llm_key:
            errors.append("❌ MINIMAX_API_KEY未在.env中设置")
        else:
            print(f"✓ MINIMAX_API_KEY已配置: {llm_key[:10]}...")
    
    # 检查dry_run设置
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    if dry_run:
        warnings.append("⚠️ DRY_RUN=true，这是测试模式，不会真正下单")
        print("⚠️ 警告: DRY_RUN=true，这是测试模式，不会真正下单")
    else:
        print("✓ 真实交易模式（dry_run=false）")
    
    print()
    
    if errors:
        print("❌ 配置错误:")
        for error in errors:
            print(f"  {error}")
        print()
        print("请修复这些错误后重新运行。")
        return False
    
    if warnings:
        print("⚠️ 警告:")
        for warning in warnings:
            print(f"  {warning}")
        print()
    
    print("✓ 所有配置验证通过")
    print()
    return True


def test_api_connection() -> bool:
    """测试API连接"""
    print("=" * 80)
    print("API连接测试")
    print("=" * 80)
    print()
    
    try:
        client = RoostooClient()
        print(f"✓ RoostooClient创建成功")
        print(f"  API URL: {client.base_url}")
        
        # 测试服务器时间
        print("\n测试服务器时间...")
        server_time = client.check_server_time()
        print(f"✓ 服务器时间: {server_time}")
        
        # 测试交易所信息
        print("\n测试获取交易所信息...")
        exchange_info = client.get_exchange_info()
        print(f"✓ 交易所信息获取成功")
        if isinstance(exchange_info, dict) and "InitialWallet" in exchange_info:
            initial_wallet = exchange_info["InitialWallet"]
            if isinstance(initial_wallet, dict) and "USD" in initial_wallet:
                print(f"✓ 初始本金: {initial_wallet['USD']} USD")
        
        # 测试市场数据
        print("\n测试获取市场数据...")
        ticker = client.get_ticker(pair="BTC/USD")
        print(f"✓ 市场数据获取成功")
        
        # 测试账户余额（可能失败，但不影响运行）
        print("\n测试获取账户余额...")
        try:
            balance = client.get_balance()
            print(f"✓ 账户余额获取成功")
        except Exception as e:
            print(f"⚠️ 账户余额获取失败: {e}")
            print("  这不会影响系统运行，系统会继续使用其他数据源")
        
        print()
        print("✓ API连接测试通过")
        print()
        return True
        
    except Exception as e:
        print(f"\n❌ API连接测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llm_connection() -> bool:
    """测试LLM连接"""
    print("=" * 80)
    print("LLM连接测试")
    print("=" * 80)
    print()
    
    try:
        provider = os.getenv("LLM_PROVIDER", "deepseek")
        llm = get_llm_client(provider=provider)
        print(f"✓ LLM客户端创建成功: {type(llm).__name__}")
        
        # 测试LLM调用
        print("\n测试LLM调用...")
        messages = [{"role": "user", "content": "Hello"}]
        response = llm.chat(messages, max_tokens=10)
        print(f"✓ LLM响应成功")
        
        print()
        print("✓ LLM连接测试通过")
        print()
        return True
        
    except Exception as e:
        print(f"\n❌ LLM连接测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_initial_capital_from_api() -> float:
    """从API获取初始本金"""
    try:
        client = RoostooClient()
        exchange_info = client.get_exchange_info()
        
        if isinstance(exchange_info, dict) and "InitialWallet" in exchange_info:
            initial_wallet = exchange_info["InitialWallet"]
            if isinstance(initial_wallet, dict) and "USD" in initial_wallet:
                initial_capital = float(initial_wallet["USD"])
                print(f"[InitialCapital] ✓ 从API获取初始本金: {initial_capital:.2f} USD")
                return initial_capital
        
        print(f"[InitialCapital] ⚠️ API响应格式不符合预期，使用默认值50000")
        return 50000.0
        
    except Exception as e:
        print(f"[InitialCapital] ⚠️ 从API获取初始本金失败: {e}")
        print(f"[InitialCapital] 使用默认值: 50000.0 USD")
        return 50000.0


def print_statistics():
    """打印运行统计信息"""
    global stats, start_time
    
    if start_time:
        elapsed = time.time() - start_time
        elapsed_min = int(elapsed / 60)
        elapsed_sec = int(elapsed % 60)
    else:
        elapsed_min = 0
        elapsed_sec = 0
    
    print("\n" + "=" * 80)
    print("运行统计")
    print("=" * 80)
    print(f"运行时长: {elapsed_min}分{elapsed_sec}秒")
    print(f"总决策数: {stats['total_decisions']}")
    print(f"总订单数: {stats['total_orders']}")
    print(f"成功订单: {stats['successful_orders']}")
    print(f"失败订单: {stats['failed_orders']}")
    
    if stats['total_orders'] > 0:
        success_rate = (stats['successful_orders'] / stats['total_orders']) * 100
        print(f"成功率: {success_rate:.2f}%")
    
    if stats['agents']:
        print("\n各Agent统计:")
        for agent_name, agent_stats in stats['agents'].items():
            print(f"  {agent_name}:")
            print(f"    决策数: {agent_stats.get('decisions', 0)}")
            print(f"    订单数: {agent_stats.get('orders', 0)}")
    
    print("=" * 80)


def main():
    """主函数"""
    global shutdown_requested, start_time, stats
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 解析运行时长参数
    run_duration_minutes = 30  # 默认30分钟
    if len(sys.argv) > 1:
        try:
            run_duration_minutes = int(sys.argv[1])
        except ValueError:
            print(f"⚠️ 无效的运行时长参数，使用默认值30分钟")
    
    print("=" * 80)
    print("生产环境交易系统")
    print("=" * 80)
    print()
    print(f"运行时长: {run_duration_minutes} 分钟")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 验证配置
    if not verify_configuration():
        print("\n❌ 配置验证失败，请修复后重新运行")
        sys.exit(1)
    
    # 2. 测试API连接
    if not test_api_connection():
        print("\n❌ API连接测试失败，请检查网络和API配置")
        sys.exit(1)
    
    # 3. 测试LLM连接
    if not test_llm_connection():
        print("\n❌ LLM连接测试失败，请检查LLM配置")
        sys.exit(1)
    
    # 4. 获取初始本金
    print("=" * 80)
    print("初始化系统")
    print("=" * 80)
    print()
    
    initial_capital = get_initial_capital_from_api()
    capital_manager = CapitalManager(initial_capital=initial_capital)
    
    # 5. 创建Agent管理器
    print("\n[1] 创建Agent管理器...")
    mgr = AgentManager()
    
    # 6. 创建Prompt管理器
    print("[2] 创建Prompt管理器...")
    prompt_mgr = PromptManager()
    
    # 7. 创建Agent
    print("[3] 创建AI Agents...")
    
    conservative_prompt = prompt_mgr.get_system_prompt(
        agent_name="ConservativeAgent",
        trading_strategy="Focus on capital preservation. Only trade on strong signals.",
        risk_level="conservative"
    )
    
    balanced_prompt = prompt_mgr.get_system_prompt(
        agent_name="BalancedAgent",
        trading_strategy="Balance risk and reward. Look for good opportunities.",
        risk_level="moderate"
    )
    
    # 8. 均分本金
    print("\n[4] 均分本金给两个Agent...")
    agent_names = ["conservative_agent", "balanced_agent"]
    allocations = capital_manager.allocate_equal(agent_names)
    capital_manager.print_summary()
    
    conservative_capital = allocations.get("conservative_agent", initial_capital / 2)
    balanced_capital = allocations.get("balanced_agent", initial_capital / 2)
    
    # 9. 添加Agent
    mgr.add_agent(
        name="conservative_agent",
        system_prompt=conservative_prompt,
        allocated_capital=conservative_capital
    )
    mgr.add_agent(
        name="balanced_agent",
        system_prompt=balanced_prompt,
        allocated_capital=balanced_capital
    )
    
    # 10. 启动Agent
    print("\n[5] 启动Agents...")
    mgr.start()
    
    # 11. 创建市场数据采集器
    print("[6] 启动市场数据采集器...")
    collector = MarketDataCollector(
        bus=mgr.bus,
        market_topic=mgr.market_topic,
        pairs=["BTC/USD"],
        collect_interval=5.0,
        collect_balance=True,
        collect_ticker=True
    )
    collector.start()
    
    # 12. 创建交易执行器（真实交易模式）
    print("[7] 启动交易执行器...")
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    
    if dry_run:
        print("⚠️ 警告: DRY_RUN=true，这是测试模式，不会真正下单")
        print("⚠️ 警告: 如需真实交易，请在.env中设置 DRY_RUN=false 或删除DRY_RUN配置")
    else:
        print("✓ 真实交易模式已启用 - 将真正执行下单操作")
    
    executor = TradeExecutor(
        bus=mgr.bus,
        decision_topic=mgr.decision_topic,
        default_pair="BTC/USD",
        dry_run=dry_run
    )
    executor.start()
    
    # 13. 等待初始数据
    print("\n[8] 等待初始市场数据...")
    time.sleep(8)
    
    # 14. 发送初始交易提示
    print("[9] 发送初始交易提示...")
    market_snapshot = collector.get_latest_snapshot()
    trading_prompt = prompt_mgr.create_trading_prompt(
        market_snapshot=market_snapshot,
        additional_context="This is the initial trading decision request. Analyze the market and provide your recommendation."
    )
    mgr.broadcast_prompt(role="user", content=trading_prompt)
    
    # 15. 主循环
    print("\n" + "=" * 80)
    print("系统运行中...")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"预计运行: {run_duration_minutes} 分钟")
    print("按 Ctrl+C 可以提前停止")
    print("=" * 80)
    print()
    
    start_time = time.time()
    run_duration_seconds = run_duration_minutes * 60
    last_stats_time = time.time()
    last_prompt_time = time.time()
    prompt_interval = 30  # 每30秒发送一次交易提示
    
    try:
        while not shutdown_requested:
            current_time = time.time()
            elapsed = current_time - start_time
            
            # 检查是否达到运行时长
            if elapsed >= run_duration_seconds:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 达到运行时长 ({run_duration_minutes} 分钟)，准备停止...")
                break
            
            # 每30秒发送一次交易提示
            if current_time - last_prompt_time >= prompt_interval:
                market_snapshot = collector.get_latest_snapshot()
                trading_prompt = prompt_mgr.create_trading_prompt(
                    market_snapshot=market_snapshot,
                    additional_context="Periodic market analysis request."
                )
                mgr.broadcast_prompt(role="user", content=trading_prompt)
                last_prompt_time = current_time
                
                elapsed_min = int(elapsed / 60)
                elapsed_sec = int(elapsed % 60)
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 发送交易提示 (运行时长: {elapsed_min}分{elapsed_sec}秒)")
            
            # 每60秒显示一次统计
            if current_time - last_stats_time >= 60:
                decisions = mgr.collect_decisions(max_items=10, wait_seconds=0.1)
                if decisions:
                    stats['total_decisions'] += len(decisions)
                    for d in decisions:
                        agent_name = d.get('agent', 'unknown')
                        if agent_name not in stats['agents']:
                            stats['agents'][agent_name] = {'decisions': 0, 'orders': 0}
                        stats['agents'][agent_name]['decisions'] += 1
                
                elapsed_min = int(elapsed / 60)
                remaining_min = run_duration_minutes - elapsed_min
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 运行中... (已运行: {elapsed_min}分钟, 剩余: {remaining_min}分钟, 决策数: {stats['total_decisions']})")
                last_stats_time = current_time
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\n收到中断信号...")
    
    # 16. 优雅关闭
    print("\n" + "=" * 80)
    print("正在关闭系统...")
    print("=" * 80)
    
    collector.stop()
    collector.join(timeout=5)
    executor.stop()
    executor.join(timeout=5)
    mgr.stop()
    
    # 17. 最终统计
    print_statistics()
    
    # 18. 最终资金摘要
    print("\n" + "=" * 80)
    print("最终资金摘要")
    print("=" * 80)
    capital_manager.print_summary()
    
    print("\n" + "=" * 80)
    print("系统已关闭")
    print("=" * 80)
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("💡 提示: 交易结果会在约30分钟后显示在leaderboard上")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n\n❌ 系统运行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

