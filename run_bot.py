#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终运行脚本 - 双Agent交易系统
满足以下要求：
1. 两个Agent平分本金，各自操作
2. 整个bot在一分钟内最多输出1次决策
3. 决策通过API正确传到市场
4. 适合在tmux中持续运行

运行方式：
    python run_bot.py

在tmux中运行：
    tmux new-session -d -s trading_bot 'python run_bot.py'
    tmux attach -t trading_bot  # 查看运行状态
    tmux kill-session -t trading_bot  # 停止运行
"""
import os
import sys
import time
import signal
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

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
logger = None


def setup_logging():
    """设置日志记录"""
    global logger
    
    # 创建logs目录
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # 日志文件名：包含日期时间
    log_filename = logs_dir / f"trading_bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # 配置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 同时输出到文件和控制台
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger('TradingBot')
    logger.info(f"日志文件: {log_filename}")
    return logger


def signal_handler(sig, frame):
    """处理停止信号，优雅关闭"""
    global shutdown_requested
    logger.info("=" * 80)
    logger.info("收到停止信号，正在优雅关闭...")
    logger.info("=" * 80)
    shutdown_requested = True


def verify_configuration() -> bool:
    """验证所有必要的配置"""
    logger.info("=" * 80)
    logger.info("配置验证")
    logger.info("=" * 80)
    
    errors = []
    
    # 检查Roostoo API配置
    api_key = os.getenv("ROOSTOO_API_KEY")
    secret_key = os.getenv("ROOSTOO_SECRET_KEY")
    api_url = os.getenv("ROOSTOO_API_URL")
    
    if not api_key:
        errors.append("❌ ROOSTOO_API_KEY未在.env中设置")
    else:
        logger.info(f"✓ ROOSTOO_API_KEY已配置: {api_key[:10]}...{api_key[-10:]}")
    
    if not secret_key:
        errors.append("❌ ROOSTOO_SECRET_KEY未在.env中设置")
    else:
        logger.info(f"✓ ROOSTOO_SECRET_KEY已配置: {secret_key[:10]}...{secret_key[-10:]}")
    
    if not api_url:
        errors.append("❌ ROOSTOO_API_URL未在.env中设置")
    else:
        logger.info(f"✓ ROOSTOO_API_URL已配置: {api_url}")
    
    # 检查LLM配置（至少需要一个LLM）
    llm_providers = []
    if os.getenv("DEEPSEEK_API_KEY"):
        llm_providers.append("deepseek")
        logger.info("✓ DEEPSEEK_API_KEY已配置")
    if os.getenv("QWEN_API_KEY"):
        llm_providers.append("qwen")
        logger.info("✓ QWEN_API_KEY已配置")
    if os.getenv("MINIMAX_API_KEY"):
        llm_providers.append("minimax")
        logger.info("✓ MINIMAX_API_KEY已配置")
    
    if not llm_providers:
        errors.append("❌ 至少需要配置一个LLM API KEY (DEEPSEEK_API_KEY/QWEN_API_KEY/MINIMAX_API_KEY)")
    
    if errors:
        logger.error("配置错误:")
        for error in errors:
            logger.error(f"  {error}")
        return False
    
    logger.info("✓ 所有配置验证通过")
    return True


def test_api_connection() -> bool:
    """测试API连接"""
    logger.info("=" * 80)
    logger.info("API连接测试")
    logger.info("=" * 80)
    
    try:
        client = RoostooClient()
        logger.info(f"✓ RoostooClient创建成功")
        logger.info(f"  API URL: {client.base_url}")
        
        # 测试服务器时间
        server_time = client.check_server_time()
        logger.info(f"✓ 服务器时间: {server_time}")
        
        # 测试交易所信息
        exchange_info = client.get_exchange_info()
        logger.info(f"✓ 交易所信息获取成功")
        
        # 测试市场数据
        ticker = client.get_ticker(pair="BTC/USD")
        logger.info(f"✓ 市场数据获取成功")
        
        # 测试账户余额
        try:
            balance = client.get_balance()
            logger.info(f"✓ 账户余额获取成功")
        except Exception as e:
            logger.warning(f"⚠️ 账户余额获取失败: {e}")
        
        logger.info("✓ API连接测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ API连接测试失败: {e}")
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
                logger.info(f"✓ 从API获取初始本金: {initial_capital:.2f} USD")
                return initial_capital
        
        logger.warning("⚠️ API响应格式不符合预期，使用默认值50000")
        return 50000.0
        
    except Exception as e:
        logger.warning(f"⚠️ 从API获取初始本金失败: {e}")
        logger.info("使用默认值: 50000.0 USD")
        return 50000.0


def main():
    """主函数"""
    global shutdown_requested, start_time, logger
    
    # 设置日志
    logger = setup_logging()
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 80)
    logger.info("双Agent交易系统启动")
    logger.info("=" * 80)
    logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    # 1. 验证配置
    if not verify_configuration():
        logger.error("配置验证失败，请修复后重新运行")
        sys.exit(1)
    
    # 2. 测试API连接
    if not test_api_connection():
        logger.error("API连接测试失败，请检查网络和API配置")
        sys.exit(1)
    
    # 3. 获取初始本金并创建资本管理器
    logger.info("=" * 80)
    logger.info("初始化系统")
    logger.info("=" * 80)
    
    initial_capital = get_initial_capital_from_api()
    capital_manager = CapitalManager(initial_capital=initial_capital)
    
    # 4. 创建Agent管理器
    logger.info("\n[1] 创建Agent管理器...")
    mgr = AgentManager()
    
    # 5. 创建Prompt管理器
    logger.info("[2] 创建Prompt管理器...")
    prompt_mgr = PromptManager()
    
    # 6. 均分本金给两个Agent
    logger.info("\n[3] 均分本金给两个Agent...")
    agent_names = ["agent_1", "agent_2"]
    allocations = capital_manager.allocate_equal(agent_names)
    capital_manager.print_summary()
    
    agent_1_capital = allocations.get("agent_1", initial_capital / 2)
    agent_2_capital = allocations.get("agent_2", initial_capital / 2)
    
    # 7. 创建两个Agent的系统提示词
    logger.info("\n[4] 创建AI Agents...")
    
    # Agent 1: 使用第一个可用的LLM
    llm_provider_1 = None
    if os.getenv("DEEPSEEK_API_KEY"):
        llm_provider_1 = "deepseek"
    elif os.getenv("QWEN_API_KEY"):
        llm_provider_1 = "qwen"
    elif os.getenv("MINIMAX_API_KEY"):
        llm_provider_1 = "minimax"
    
    # Agent 2: 使用第二个可用的LLM（如果只有一个，则使用同一个）
    llm_provider_2 = None
    if os.getenv("QWEN_API_KEY") and llm_provider_1 != "qwen":
        llm_provider_2 = "qwen"
    elif os.getenv("DEEPSEEK_API_KEY") and llm_provider_1 != "deepseek":
        llm_provider_2 = "deepseek"
    elif os.getenv("MINIMAX_API_KEY") and llm_provider_1 != "minimax":
        llm_provider_2 = "minimax"
    else:
        llm_provider_2 = llm_provider_1  # 如果只有一个LLM，两个Agent使用同一个
    
    # 创建系统提示词
    agent_1_prompt = prompt_mgr.get_system_prompt(
        agent_name="Agent1",
        trading_strategy="Focus on capital preservation and risk management. Make conservative trading decisions.",
        risk_level="conservative"
    )
    
    agent_2_prompt = prompt_mgr.get_system_prompt(
        agent_name="Agent2",
        trading_strategy="Balance risk and reward. Look for good trading opportunities with moderate risk.",
        risk_level="moderate"
    )
    
    # 8. 添加Agent
    logger.info(f"[5] 添加Agent 1 (LLM: {llm_provider_1}, 资金: {agent_1_capital:.2f} USD)...")
    mgr.add_agent(
        name="agent_1",
        system_prompt=agent_1_prompt,
        llm_provider=llm_provider_1,
        allocated_capital=agent_1_capital
    )
    
    logger.info(f"[6] 添加Agent 2 (LLM: {llm_provider_2}, 资金: {agent_2_capital:.2f} USD)...")
    mgr.add_agent(
        name="agent_2",
        system_prompt=agent_2_prompt,
        llm_provider=llm_provider_2,
        allocated_capital=agent_2_capital
    )
    
    # 9. 启动Agent
    logger.info("\n[7] 启动Agents...")
    mgr.start()
    
    # 10. 创建市场数据采集器
    logger.info("[8] 启动市场数据采集器...")
    collector = MarketDataCollector(
        bus=mgr.bus,
        market_topic=mgr.market_topic,
        pairs=["BTC/USD"],
        collect_interval=12.0,  # 12秒间隔，符合每分钟最多5次API调用的限制
        collect_balance=True,
        collect_ticker=True
    )
    collector.start()
    
    # 11. 创建交易执行器（真实交易模式）
    logger.info("[9] 启动交易执行器...")
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    
    if dry_run:
        logger.warning("⚠️ 警告: DRY_RUN=true，这是测试模式，不会真正下单")
    else:
        logger.info("✓ 真实交易模式已启用 - 将真正执行下单操作")
    
    executor = TradeExecutor(
        bus=mgr.bus,
        decision_topic=mgr.decision_topic,
        default_pair="BTC/USD",
        dry_run=dry_run
    )
    executor.start()
    
    # 12. 等待初始数据
    logger.info("\n[10] 等待初始市场数据...")
    time.sleep(8)
    
    # 13. 发送初始交易提示
    logger.info("[11] 发送初始交易提示...")
    market_snapshot = collector.get_latest_snapshot()
    if market_snapshot:
        trading_prompt = prompt_mgr.create_trading_prompt(
            market_snapshot=market_snapshot,
            additional_context="This is the initial trading decision request. Analyze the market and provide your recommendation."
        )
        mgr.broadcast_prompt(role="user", content=trading_prompt)
    
    # 14. 主循环
    logger.info("\n" + "=" * 80)
    logger.info("系统运行中...")
    logger.info("=" * 80)
    logger.info("系统配置:")
    logger.info(f"  - 两个Agent平分本金: {agent_1_capital:.2f} USD / {agent_2_capital:.2f} USD")
    logger.info(f"  - 全局决策频率限制: 每分钟最多1次")
    logger.info(f"  - API调用频率限制: 每分钟最多5次")
    logger.info(f"  - 交易模式: {'测试模式 (DRY_RUN)' if dry_run else '真实交易模式'}")
    logger.info("=" * 80)
    logger.info("按 Ctrl+C 可以停止")
    logger.info("=" * 80)
    
    start_time = time.time()
    last_prompt_time = time.time()
    prompt_interval = 30  # 每30秒发送一次交易提示
    stats_interval = 60  # 每60秒显示一次统计
    last_stats_time = time.time()
    
    decision_count = 0
    order_count = 0
    
    try:
        while not shutdown_requested:
            current_time = time.time()
            elapsed = current_time - start_time
            
            # 每30秒发送一次交易提示
            if current_time - last_prompt_time >= prompt_interval:
                market_snapshot = collector.get_latest_snapshot()
                if market_snapshot:
                    trading_prompt = prompt_mgr.create_trading_prompt(
                        market_snapshot=market_snapshot,
                        additional_context="Periodic market analysis request."
                    )
                    mgr.broadcast_prompt(role="user", content=trading_prompt)
                    last_prompt_time = current_time
                    
                    elapsed_min = int(elapsed / 60)
                    elapsed_sec = int(elapsed % 60)
                    logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] 发送交易提示 (运行时长: {elapsed_min}分{elapsed_sec}秒)")
            
            # 每60秒显示一次统计
            if current_time - last_stats_time >= stats_interval:
                elapsed_min = int(elapsed / 60)
                logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] 运行中... (已运行: {elapsed_min}分钟, 决策数: {decision_count}, 订单数: {order_count})")
                last_stats_time = current_time
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("\n收到中断信号...")
    
    # 15. 优雅关闭
    logger.info("\n" + "=" * 80)
    logger.info("正在关闭系统...")
    logger.info("=" * 80)
    
    collector.stop()
    collector.join(timeout=5)
    executor.stop()
    executor.join(timeout=5)
    mgr.stop()
    
    # 16. 最终统计
    elapsed = time.time() - start_time
    elapsed_min = int(elapsed / 60)
    elapsed_sec = int(elapsed % 60)
    
    logger.info("\n" + "=" * 80)
    logger.info("运行统计")
    logger.info("=" * 80)
    logger.info(f"运行时长: {elapsed_min}分{elapsed_sec}秒")
    logger.info(f"决策数: {decision_count}")
    logger.info(f"订单数: {order_count}")
    
    # 17. 最终资金摘要
    logger.info("\n" + "=" * 80)
    logger.info("最终资金摘要")
    logger.info("=" * 80)
    capital_manager.print_summary()
    
    logger.info("\n" + "=" * 80)
    logger.info("系统已关闭")
    logger.info("=" * 80)
    logger.info(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        if logger:
            logger.error(f"系统运行出错: {e}")
        else:
            print(f"系统运行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

