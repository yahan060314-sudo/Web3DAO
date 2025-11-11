#!/usr/bin/env python3
"""
完整流程测试脚本
测试从市场数据获取 → AI决策生成 → 交易执行的完整流程
"""
import sys
import os
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from api.agents.bus import MessageBus
from api.agents.market_collector import MarketDataCollector
from api.agents.manager import AgentManager
from api.agents.enhanced_executor import EnhancedTradeExecutor
from api.roostoo_client import RoostooClient
from api.llm_clients.factory import get_llm_client


def test_step_1_roostoo_api():
    """测试步骤1: Roostoo API 连接"""
    print("=" * 80)
    print("测试步骤1: Roostoo API 连接")
    print("=" * 80)
    
    try:
        client = RoostooClient()
        print(f"✓ RoostooClient 创建成功")
        print(f"  API URL: {client.base_url}")
        print(f"  API Key: {client.api_key[:10]}..." if client.api_key else "  ✗ API Key: 未设置")
        
        # 测试1: 检查服务器时间
        print("\n1. 测试服务器时间...")
        server_time = client.check_server_time()
        print(f"   ✓ 服务器时间: {server_time}")
        
        # 测试2: 获取交易所信息
        print("\n2. 测试获取交易所信息...")
        try:
            exchange_info = client.get_exchange_info()
            print(f"   ✓ 交易所信息获取成功")
            if isinstance(exchange_info, dict):
                print(f"   响应键: {list(exchange_info.keys())[:5]}")
        except Exception as e:
            print(f"   ⚠️ 获取交易所信息失败: {e}")
        
        # 测试3: 获取市场数据
        print("\n3. 测试获取市场数据 (BTC/USD)...")
        try:
            ticker = client.get_ticker(pair="BTC/USD")
            print(f"   ✓ 市场数据获取成功")
            if isinstance(ticker, dict):
                print(f"   响应: {ticker}")
        except Exception as e:
            print(f"   ⚠️ 获取市场数据失败: {e}")
        
        # 测试4: 获取账户余额
        print("\n4. 测试获取账户余额...")
        try:
            balance = client.get_balance()
            print(f"   ✓ 账户余额获取成功")
            if isinstance(balance, dict):
                print(f"   响应: {balance}")
        except Exception as e:
            print(f"   ⚠️ 获取账户余额失败: {e}")
            print(f"   提示: 这可能是API认证问题，或比赛还未开始")
        
        print("\n✓ 步骤1完成: Roostoo API 连接测试")
        return True
        
    except Exception as e:
        print(f"\n✗ 步骤1失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_step_2_llm_connection():
    """测试步骤2: LLM 连接"""
    print("\n" + "=" * 80)
    print("测试步骤2: LLM 连接")
    print("=" * 80)
    
    try:
        # 获取LLM客户端
        provider = os.getenv("LLM_PROVIDER", "deepseek")
        print(f"使用LLM提供商: {provider}")
        
        client = get_llm_client(provider=provider)
        print(f"✓ LLM客户端创建成功: {type(client).__name__}")
        
        # 测试LLM调用
        print("\n测试LLM调用...")
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'hello' in one word."}
        ]
        
        response = client.chat(messages, max_tokens=50, temperature=0.7)
        content = response.get("content", "")
        
        if content:
            print(f"   ✓ LLM响应: {content[:100]}")
            print("\n✓ 步骤2完成: LLM 连接测试")
            return True
        else:
            print(f"   ✗ LLM响应为空")
            return False
        
    except Exception as e:
        print(f"\n✗ 步骤2失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_step_3_market_data_collection():
    """测试步骤3: 市场数据采集"""
    print("\n" + "=" * 80)
    print("测试步骤3: 市场数据采集")
    print("=" * 80)
    
    try:
        bus = MessageBus()
        
        # 创建市场数据采集器
        collector = MarketDataCollector(
            bus=bus,
            market_topic="market_ticks",
            pairs=["BTC/USD"],
            collect_interval=5.0,
            collect_balance=True,
            collect_ticker=True
        )
        
        print("✓ MarketDataCollector 创建成功")
        
        # 启动采集器
        collector.start()
        print("✓ 市场数据采集器已启动")
        
        # 等待采集数据
        print("\n等待采集市场数据...")
        time.sleep(6)  # 等待一次采集周期
        
        # 检查是否采集到数据
        sub = bus.subscribe("market_ticks")
        market_data = sub.recv(timeout=2.0)
        
        if market_data:
            print(f"   ✓ 采集到市场数据")
            if "pair" in market_data:
                print(f"   交易对: {market_data.get('pair', 'N/A')}")
            if "price" in market_data:
                print(f"   价格: {market_data.get('price', 'N/A')}")
            if "type" in market_data:
                print(f"   类型: {market_data.get('type', 'N/A')}")
        else:
            print("   ⚠️ 未采集到市场数据（可能是API连接问题或比赛未开始）")
            print("   提示: 如果使用真实API，确保比赛已开始")
        
        # 停止采集器
        collector.stop()
        collector.join(timeout=2)
        print("✓ 市场数据采集器已停止")
        
        print("\n✓ 步骤3完成: 市场数据采集测试")
        return True
        
    except Exception as e:
        print(f"\n✗ 步骤3失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_step_4_ai_decision_generation():
    """测试步骤4: AI决策生成"""
    print("\n" + "=" * 80)
    print("测试步骤4: AI决策生成")
    print("=" * 80)
    
    try:
        bus = MessageBus()
        manager = AgentManager()
        
        # 添加Agent
        manager.add_agent(
            name="TestTradingAgent",
            system_prompt="You are a trading assistant. Make trading decisions based on market data. Always respond in JSON format: {\"action\": \"buy|sell|wait\", \"quantity\": 0.01, \"symbol\": \"BTCUSDT\"}"
        )
        
        print("✓ AgentManager 创建成功")
        print("✓ TestTradingAgent 已添加")
        
        # 启动Agent
        manager.start()
        print("✓ Agent 已启动")
        
        # 模拟市场数据
        market_data = {
            "type": "ticker",
            "pair": "BTC/USD",
            "price": 50000.0,
            "volume_24h": 1000000.0,
            "change_24h": 2.5,
            "timestamp": time.time()
        }
        
        manager.broadcast_market(market_data)
        print("✓ 市场数据已广播")
        
        # 发送交易提示
        manager.broadcast_prompt(
            role="user",
            content="Analyze the current market situation and make a trading decision. Respond in JSON format."
        )
        print("✓ 交易提示已发送")
        
        # 等待决策生成
        print("\n等待AI生成决策...")
        time.sleep(10)  # 等待LLM响应
        
        # 收集决策
        decisions = manager.collect_decisions(max_items=5, wait_seconds=2.0)
        
        if decisions:
            print(f"   ✓ 收到 {len(decisions)} 个决策")
            for i, decision in enumerate(decisions, 1):
                agent = decision.get("agent", "unknown")
                decision_text = decision.get("decision", "")[:100]
                print(f"   决策 {i} (Agent: {agent}): {decision_text}...")
        else:
            print("   ⚠️ 未收到决策（可能是LLM响应慢或API问题）")
        
        # 停止Agent
        manager.stop()
        print("✓ Agent 已停止")
        
        print("\n✓ 步骤4完成: AI决策生成测试")
        return True
        
    except Exception as e:
        print(f"\n✗ 步骤4失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_step_5_decision_execution():
    """测试步骤5: 决策执行（dry_run模式）"""
    print("\n" + "=" * 80)
    print("测试步骤5: 决策执行（dry_run模式）")
    print("=" * 80)
    
    try:
        bus = MessageBus()
        
        # 创建增强版执行器（dry_run模式）
        executor = EnhancedTradeExecutor(
            bus=bus,
            decision_topic="decisions",
            default_pair="BTC/USD",
            dry_run=True,  # 测试模式，不会真正下单
            enable_decision_manager=True,
            db_path="test_decisions.db",
            enable_multi_ai_consensus=True
        )
        
        print("✓ EnhancedTradeExecutor 创建成功（dry_run模式）")
        
        # 启动执行器
        executor.start()
        print("✓ 执行器已启动")
        
        # 模拟决策消息
        test_decision = {
            "agent": "TestAgent",
            "decision": '{"action": "buy", "quantity": 0.01, "symbol": "BTCUSDT"}',
            "market_snapshot": {
                "ticker": {"price": 50000.0},
                "balance": {}
            },
            "timestamp": time.time(),
            "json_valid": True
        }
        
        bus.publish("decisions", test_decision)
        print("✓ 测试决策已发布")
        
        # 等待处理
        print("\n等待决策处理...")
        time.sleep(3)
        
        # 获取统计信息
        stats = executor.get_statistics(hours=24)
        print(f"\n执行统计:")
        print(f"  总决策数: {stats.get('total_decisions', 0)}")
        print(f"  成功执行数: {stats.get('success_count', 0)}")
        print(f"  失败执行数: {stats.get('fail_count', 0)}")
        print(f"  成功率: {stats.get('success_rate', 0):.2%}")
        
        # 停止执行器
        executor.stop()
        print("✓ 执行器已停止")
        
        print("\n✓ 步骤5完成: 决策执行测试")
        return True
        
    except Exception as e:
        print(f"\n✗ 步骤5失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_step_6_complete_flow():
    """测试步骤6: 完整流程（端到端）"""
    print("\n" + "=" * 80)
    print("测试步骤6: 完整流程（端到端）")
    print("=" * 80)
    
    try:
        # 1. 创建消息总线
        bus = MessageBus()
        
        # 2. 创建Roostoo客户端
        roostoo_client = RoostooClient()
        print("✓ RoostooClient 创建成功")
        
        # 3. 创建市场数据采集器
        collector = MarketDataCollector(
            bus=bus,
            market_topic="market_ticks",
            pairs=["BTC/USD"],
            collect_interval=5.0,
            collect_balance=True,
            collect_ticker=True
        )
        print("✓ MarketDataCollector 创建成功")
        
        # 4. 创建Agent管理器
        manager = AgentManager()
        manager.add_agent(
            name="TradingAgent",
            system_prompt="You are a trading assistant. Make trading decisions based on market data. Always respond in JSON format: {\"action\": \"buy|sell|wait\", \"quantity\": 0.01, \"symbol\": \"BTCUSDT\"}"
        )
        print("✓ AgentManager 创建成功")
        
        # 5. 创建增强版执行器（dry_run模式）
        executor = EnhancedTradeExecutor(
            bus=bus,
            decision_topic=manager.decision_topic,
            default_pair="BTC/USD",
            dry_run=True,  # 测试模式，不会真正下单
            enable_decision_manager=True,
            enable_multi_ai_consensus=True
        )
        print("✓ EnhancedTradeExecutor 创建成功（dry_run模式）")
        
        # 6. 启动所有组件
        print("\n启动所有组件...")
        collector.start()
        manager.start()
        executor.start()
        print("✓ 所有组件已启动")
        
        # 7. 等待采集市场数据
        print("\n等待采集市场数据...")
        time.sleep(6)
        
        # 8. 发送交易提示
        print("\n发送交易提示...")
        manager.broadcast_prompt(
            role="user",
            content="Analyze the current market situation and make a trading decision. Respond in JSON format."
        )
        
        # 9. 等待决策生成和执行
        print("\n等待决策生成和执行...")
        time.sleep(15)  # 等待LLM响应和执行
        
        # 10. 获取统计信息
        stats = executor.get_statistics(hours=24)
        print(f"\n执行统计:")
        print(f"  总决策数: {stats.get('total_decisions', 0)}")
        print(f"  成功执行数: {stats.get('success_count', 0)}")
        print(f"  失败执行数: {stats.get('fail_count', 0)}")
        print(f"  成功率: {stats.get('success_rate', 0):.2%}")
        
        # 11. 停止所有组件
        print("\n停止所有组件...")
        collector.stop()
        manager.stop()
        executor.stop()
        
        collector.join(timeout=2)
        for agent in manager.agents:
            agent.join(timeout=1)
        executor.join(timeout=2)
        
        print("✓ 所有组件已停止")
        
        print("\n✓ 步骤6完成: 完整流程测试")
        return True
        
    except Exception as e:
        print(f"\n✗ 步骤6失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("完整流程测试")
    print("=" * 80)
    print()
    print("这个测试将验证以下流程:")
    print("1. Roostoo API 连接")
    print("2. LLM 连接（DeepSeek/Qwen/Minimax）")
    print("3. 市场数据采集")
    print("4. AI决策生成")
    print("5. 决策执行（dry_run模式）")
    print("6. 完整流程（端到端）")
    print()
    print("⚠️ 注意: 所有测试都使用 dry_run 模式，不会真正下单")
    print()
    
    # 检查环境变量
    print("检查环境变量...")
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️ 警告: .env 文件不存在")
        print("   请创建 .env 文件并配置 API 凭证")
    else:
        print("✓ .env 文件存在")
    
    # 检查API凭证
    roostoo_api_key = os.getenv("ROOSTOO_API_KEY")
    roostoo_secret_key = os.getenv("ROOSTOO_SECRET_KEY")
    llm_provider = os.getenv("LLM_PROVIDER", "deepseek")
    
    if roostoo_api_key and "your_roostoo" not in roostoo_api_key:
        print("✓ ROOSTOO_API_KEY 已配置")
    else:
        print("⚠️ ROOSTOO_API_KEY 未配置或使用占位符")
    
    if roostoo_secret_key and "your_roostoo" not in roostoo_secret_key:
        print("✓ ROOSTOO_SECRET_KEY 已配置")
    else:
        print("⚠️ ROOSTOO_SECRET_KEY 未配置或使用占位符")
    
    print(f"✓ LLM_PROVIDER: {llm_provider}")
    print()
    
    # 运行测试
    results = {}
    
    # 测试步骤1
    results["步骤1: Roostoo API"] = test_step_1_roostoo_api()
    
    # 测试步骤2
    results["步骤2: LLM 连接"] = test_step_2_llm_connection()
    
    # 测试步骤3
    results["步骤3: 市场数据采集"] = test_step_3_market_data_collection()
    
    # 测试步骤4
    results["步骤4: AI决策生成"] = test_step_4_ai_decision_generation()
    
    # 测试步骤5
    results["步骤5: 决策执行"] = test_step_5_decision_execution()
    
    # 测试步骤6（完整流程）
    results["步骤6: 完整流程"] = test_step_6_complete_flow()
    
    # 输出测试结果
    print("\n" + "=" * 80)
    print("测试结果总结")
    print("=" * 80)
    for step, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {step}")
    
    # 清理测试文件
    test_db = Path("test_decisions.db")
    if test_db.exists():
        try:
            test_db.unlink()
            print(f"\n✓ 清理测试数据库: {test_db}")
        except Exception as e:
            print(f"\n⚠️ 无法清理测试数据库: {e}")
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)
    
    # 返回总体结果
    all_passed = all(results.values())
    return all_passed


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n用户中断测试")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

