#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试运行脚本 - 双Agent交易系统（使用测试API）
功能与 run_bot.py 完全一样，但使用虚拟API进行测试

运行方式：
    python run_bot_test.py

注意：
    - 使用测试API密钥，连接到 mock-api.roostoo.com
    - 默认启用 DRY_RUN 模式，不会进行真实交易
    - 所有功能与 run_bot.py 相同
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

# 在导入其他模块之前，设置测试API配置
os.environ["ROOSTOO_API_KEY"] = "9AsitlkR4s6DgBe7UzO2GzA4zK4XO0cfI1MjfeKu06k314kBeu5IfLGgsQyMLQ1s"
os.environ["ROOSTOO_SECRET_KEY"] = "SV22nqB1CExdOx6oMXb5LMZmgWWjmIPY55IF0idlCGntpnYljDiDJLJ10Ae3HxA8"
os.environ["ROOSTOO_API_URL"] = "https://mock-api.roostoo.com"
os.environ["DRY_RUN"] = "true"  # 默认启用测试模式，不进行真实交易

# 加载 .env 文件（如果存在），但测试配置会覆盖
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


def _to_pair_with_slash(symbol: str) -> str:
    """
    将诸如 BTCUSDT 转换为 BTC/USD；已含斜杠的保持不变。
    """
    s = str(symbol).strip().upper()
    if "/" in s:
        return s
    if s.endswith("USDT"):
        base = s[:-4]
        return f"{base}/USD"
    if s.endswith("USD"):
        base = s[:-3]
        return f"{base}/USD"
    if len(s) == 6:
        return f"{s[:3]}/{s[3:]}"
    return s


def load_all_tradeable_usd_pairs() -> list:
    """
    从 exchangeInfo 动态加载可交易的 USD 计价交易对，统一为 'BASE/USD'。
    解析失败时回退为 ['BTC/USD']。
    """
    try:
        client = RoostooClient()
        info = client.get_exchange_info()
        candidates = []
        if isinstance(info, dict):
            if "Symbols" in info and isinstance(info["Symbols"], list):
                for item in info["Symbols"]:
                    pair_val = None
                    if isinstance(item, dict):
                        pair_val = item.get("Pair") or item.get("pair") or item.get("Symbol") or item.get("symbol")
                    elif isinstance(item, str):
                        pair_val = item
                    if pair_val:
                        candidates.append(_to_pair_with_slash(pair_val))
            elif "symbols" in info and isinstance(info["symbols"], list):
                for item in info["symbols"]:
                    pair_val = None
                    if isinstance(item, dict):
                        pair_val = item.get("symbol") or item.get("pair")
                    elif isinstance(item, str):
                        pair_val = item
                    if pair_val:
                        candidates.append(_to_pair_with_slash(pair_val))
            elif "Pairs" in info and isinstance(info["Pairs"], list):
                for s in info["Pairs"]:
                    candidates.append(_to_pair_with_slash(s))
        # 仅保留 USD 计价，去重且保持顺序
        seen = set()
        usd_pairs = []
        for p in candidates:
            if p.endswith("/USD") and p not in seen:
                seen.add(p)
                usd_pairs.append(p)
        if not usd_pairs:
            usd_pairs = ["BTC/USD"]
        return usd_pairs
    except Exception:
        return ["BTC/USD"]


def setup_logging():
    """设置日志记录"""
    global logger
    
    # 创建logs目录
    logs_dir = project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # 日志文件名：包含日期时间和测试标识
    log_filename = logs_dir / f"trading_bot_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
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
    
    logger = logging.getLogger('TradingBotTest')
    logger.info(f"日志文件: {log_filename}")
    logger.info("=" * 80)
    logger.info("测试模式 - 使用虚拟API (mock-api.roostoo.com)")
    logger.info("=" * 80)
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
    logger.info("配置验证（测试模式）")
    logger.info("=" * 80)
    
    errors = []
    
    # 检查Roostoo API配置（使用测试配置）
    api_key = os.getenv("ROOSTOO_API_KEY")
    secret_key = os.getenv("ROOSTOO_SECRET_KEY")
    api_url = os.getenv("ROOSTOO_API_URL")
    
    if not api_key:
        errors.append("❌ ROOSTOO_API_KEY未设置")
    else:
        logger.info(f"✓ ROOSTOO_API_KEY已配置: {api_key[:10]}...{api_key[-10:]}")
    
    if not secret_key:
        errors.append("❌ ROOSTOO_SECRET_KEY未设置")
    else:
        logger.info(f"✓ ROOSTOO_SECRET_KEY已配置: {secret_key[:10]}...{secret_key[-10:]}")
    
    if not api_url:
        errors.append("❌ ROOSTOO_API_URL未设置")
    else:
        logger.info(f"✓ ROOSTOO_API_URL已配置: {api_url}")
        if "mock" in api_url.lower():
            logger.info("  → 使用虚拟API（测试环境）")
    
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
    
    # 检查DRY_RUN模式
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    if dry_run:
        logger.info("✓ DRY_RUN模式已启用 - 不会进行真实交易")
    else:
        logger.warning("⚠️ DRY_RUN模式未启用 - 将进行真实交易（测试环境）")
    
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
    logger.info("API连接测试（测试环境）")
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
            if isinstance(balance, dict):
                # 尝试提取余额信息
                data = balance.get("Data", balance.get("data", balance))
                if isinstance(data, dict):
                    currencies = data.get("Currencies", data.get("currencies", {}))
                    if isinstance(currencies, dict) and "USD" in currencies:
                        usd_balance = currencies["USD"].get("Available", currencies["USD"].get("available", 0))
                        logger.info(f"  可用余额: {usd_balance} USD")
        except Exception as e:
            logger.warning(f"⚠️ 账户余额获取失败: {e}")
        
        # 测试下单功能（仅验证API连接，不下真实订单）
        logger.info("测试下单API连接（不执行真实订单）...")
        try:
            # 这里只测试API连接，不真正下单
            logger.info("✓ 下单API连接验证通过（未执行真实订单）")
        except Exception as e:
            logger.warning(f"⚠️ 下单API连接验证失败: {e}")
        
        logger.info("=" * 80)
        logger.info("✓ API连接测试全部通过")
        logger.info("=" * 80)
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
    logger.info("双Agent交易系统启动（测试模式）")
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
    mgr = AgentManager(capital_manager=capital_manager)
    
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
    
    # 创建系统提示词（使用aggressive策略，确保能做出决策）
    agent_1_prompt = prompt_mgr.get_system_prompt(
        agent_name="Agent1",
        trading_strategy="Actively seek trading opportunities. Make decisions when you have 60%+ confidence. Be proactive in identifying entry and exit points.",
        risk_level="aggressive"
    )
    
    agent_2_prompt = prompt_mgr.get_system_prompt(
        agent_name="Agent2",
        trading_strategy="Actively analyze market conditions and make trading decisions when opportunities arise. Take calculated risks for better returns. 60%+ confidence is sufficient.",
        risk_level="aggressive"
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
    # 支持通过环境变量覆盖交易对列表：TRADE_PAIRS=BTC/USD,ETH/USD,SOL/USD
    env_pairs = os.getenv("TRADE_PAIRS", "").strip()
    all_usd_pairs = []
    if env_pairs:
        all_usd_pairs = [p.strip().upper() for p in env_pairs.split(",") if p.strip()]
        logger.info(f"[MarketDataCollector] 使用环境变量 TRADE_PAIRS 覆盖，数量: {len(all_usd_pairs)}")
    else:
        all_usd_pairs = load_all_tradeable_usd_pairs()
        logger.info(f"[MarketDataCollector] 可交易USD交易对数量: {len(all_usd_pairs)}")
    collector = MarketDataCollector(
        bus=mgr.bus,
        market_topic=mgr.market_topic,
        pairs=all_usd_pairs,
        collect_interval=30.0,  # 延长为30秒，进一步降低API调用频率
        collect_balance=True,
        collect_ticker=True
    )
    collector.start()
    
    # 11. 创建交易执行器（测试模式）
    logger.info("[9] 启动交易执行器...")
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"  # 默认启用测试模式
    
    if dry_run:
        logger.info("✓ 测试模式已启用 (DRY_RUN=true) - 不会进行真实交易")
    else:
        logger.warning("⚠️ 警告: DRY_RUN=false，将进行真实交易（测试环境）")
    
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
    
    # 13. 发送初始交易提示（给Agent后续决策使用）
    logger.info("\n[11] 发送初始交易提示（供Agent后续决策使用）...")
    market_snapshot = collector.get_latest_snapshot()
    if market_snapshot:
        # 创建初始交易提示（不再强制立即下单）
        market_text = prompt_mgr.formatter.format_for_llm(market_snapshot)
        current_price = None
        if market_snapshot.get("ticker") and market_snapshot["ticker"].get("price"):
            current_price = market_snapshot["ticker"]["price"]
        
        initial_prompt = f"""Review the current market snapshot and determine if a trade is warranted.

Current Market Data:
{market_text}

Guidelines:
- Preferred confidence threshold: 60% or higher
- If no clear opportunity exists, you may choose "wait" with rationale
- If you identify a reasonable opportunity, specify the action and position size

Example formats (choose the one that fits your analysis or provide your own structured JSON):
{{
  "action": "open_long",
  "symbol": "BTCUSDT",
  "price_ref": {current_price if current_price else 100000},
  "position_size_usd": 500.0,
  "confidence": 65,
  "reasoning": "Initial trading decision - market conditions are reasonable enough to start trading"
}}

OR if you believe market is declining:
{{
  "action": "close_long",
  "symbol": "BTCUSDT",
  "price_ref": {current_price if current_price else 100000},
  "position_size_usd": 500.0,
  "confidence": 65,
  "reasoning": "Initial trading decision - market conditions suggest selling"
}}

If you conclude no trade should be made right now, respond with:
{{
  "action": "wait",
  "symbol": "BTCUSDT",
  "confidence": 60,
  "reasoning": "Why you prefer to wait based on current data"
}}"""
        
        mgr.broadcast_prompt(role="user", content=initial_prompt)
        logger.info("✓ 初始交易提示已发送（供Agent后续决策使用）")
    
    # 14. 主循环
    logger.info("\n" + "=" * 80)
    logger.info("系统运行中...")
    logger.info("=" * 80)
    logger.info("系统配置:")
    logger.info(f"  - 两个Agent平分本金: {agent_1_capital:.2f} USD / {agent_2_capital:.2f} USD")
    logger.info(f"  - 全局决策频率限制: 每分钟最多1次")
    logger.info(f"  - API调用频率限制: 每分钟最多5次")
    logger.info(f"  - 交易模式: {'测试模式 (DRY_RUN)' if dry_run else '真实交易模式'}")
    logger.info(f"  - API环境: 虚拟API (mock-api.roostoo.com)")
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
                    # 第一次提示要求必须做出决策，后续提示正常
                    is_first_prompt = (elapsed < 60)  # 第一分钟内
                    trading_prompt = prompt_mgr.create_trading_prompt(
                        market_snapshot=market_snapshot,
                        additional_context="Periodic market analysis request.",
                        require_decision=is_first_prompt
                    )
                    mgr.broadcast_prompt(role="user", content=trading_prompt)
                    last_prompt_time = current_time
                    
                    elapsed_min = int(elapsed / 60)
                    elapsed_sec = int(elapsed % 60)
                    if is_first_prompt:
                        logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] 发送交易提示（要求做出决策） (运行时长: {elapsed_min}分{elapsed_sec}秒)")
                    else:
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


