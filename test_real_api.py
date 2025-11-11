#!/usr/bin/env python3
"""
测试真实 Roostoo API 连接
用于验证真实的API凭证和连接
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

from api.roostoo_client import RoostooClient


def test_api_connection():
    """测试API连接"""
    print("=" * 80)
    print("测试真实 Roostoo API 连接")
    print("=" * 80)
    print()
    
    # 检查环境变量
    api_key = os.getenv("ROOSTOO_API_KEY")
    secret_key = os.getenv("ROOSTOO_SECRET_KEY")
    api_url = os.getenv("ROOSTOO_API_URL", "https://mock-api.roostoo.com")
    
    print("配置检查:")
    print(f"  API URL: {api_url}")
    if api_key:
        print(f"  API Key: {api_key[:10]}...{api_key[-10:]}")
    else:
        print("  ✗ API Key: 未设置")
        return False
    
    if secret_key:
        print(f"  Secret Key: {secret_key[:10]}...{secret_key[-10:]}")
    else:
        print("  ✗ Secret Key: 未设置")
        return False
    
    print()
    
    # 创建客户端
    try:
        print("创建 RoostooClient...")
        client = RoostooClient()
        print(f"✓ 客户端创建成功")
        print(f"  使用的API URL: {client.base_url}")
        print()
    except Exception as e:
        print(f"✗ 创建客户端失败: {e}")
        return False
    
    # 测试1: 检查服务器时间
    print("测试1: 检查服务器时间...")
    try:
        server_time = client.check_server_time()
        print(f"✓ 服务器时间获取成功")
        print(f"  响应: {server_time}")
        print()
    except Exception as e:
        print(f"✗ 获取服务器时间失败: {e}")
        print("  提示: 可能是API URL不正确，或者API服务未启动")
        return False
    
    # 测试2: 获取交易所信息
    print("测试2: 获取交易所信息...")
    try:
        exchange_info = client.get_exchange_info()
        print(f"✓ 交易所信息获取成功")
        if isinstance(exchange_info, dict):
            print(f"  响应键: {list(exchange_info.keys())[:5]}...")
        print()
    except Exception as e:
        print(f"✗ 获取交易所信息失败: {e}")
        print("  提示: 这个API可能需要认证，或者API URL不正确")
        # 不返回False，因为某些API可能需要特殊权限
    
    # 测试3: 获取账户余额
    print("测试3: 获取账户余额...")
    try:
        balance = client.get_balance()
        print(f"✓ 账户余额获取成功")
        print(f"  响应: {balance}")
        print()
    except Exception as e:
        print(f"✗ 获取账户余额失败: {e}")
        print("  提示: 这个API需要认证，如果失败可能是:")
        print("    1. API Key 或 Secret Key 不正确")
        print("    2. API URL 不正确")
        print("    3. 签名算法不正确")
        print("    4. API服务未启动（比赛还未开始）")
        # 不返回False，因为比赛可能还没开始
    
    # 测试4: 获取市场数据
    print("测试4: 获取市场数据 (BTC/USD)...")
    try:
        ticker = client.get_ticker(pair="BTC/USD")
        print(f"✓ 市场数据获取成功")
        print(f"  响应: {ticker}")
        print()
    except Exception as e:
        print(f"✗ 获取市场数据失败: {e}")
        print("  提示: 可能是交易对名称不正确，或API服务未启动")
        # 不返回False
    
    print("=" * 80)
    print("测试完成！")
    print("=" * 80)
    print()
    print("总结:")
    print("  ✓ 如果所有测试都成功，说明API配置正确")
    print("  ⚠️ 如果某些测试失败，可能是:")
    print("    1. 比赛还未开始（API服务未启动）")
    print("    2. API URL不正确")
    print("    3. API凭证不正确")
    print("    4. 网络问题")
    print()
    
    return True


def test_place_order_dry_run():
    """测试下单功能（dry_run模式，不会真正下单）"""
    print("=" * 80)
    print("测试下单功能（dry_run模式）")
    print("=" * 80)
    print()
    print("⚠️ 注意: 这个测试不会真正下单，只是测试API调用")
    print()
    
    try:
        client = RoostooClient()
        print(f"使用API URL: {client.base_url}")
        print()
        
        # 注意：这里我们不真正调用place_order，因为可能会真的下单
        # 我们只测试客户端是否可以正常创建
        print("✓ 客户端已准备就绪")
        print("  下单功能需要在 dry_run 模式下测试")
        print("  请使用 EnhancedTradeExecutor 进行测试（dry_run=True）")
        print()
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False
    
    return True


if __name__ == "__main__":
    print()
    print("=" * 80)
    print("真实 Roostoo API 测试")
    print("=" * 80)
    print()
    print("比赛信息:")
    print("  开始时间: 2025年11月10日 晚上8点 HKT")
    print("  状态: 请确认比赛是否已开始")
    print()
    
    # 检查.env文件
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️ 警告: .env 文件不存在")
        print("  请创建 .env 文件并配置API凭证")
        print("  可以参考 .env.example 文件")
        print()
        sys.exit(1)
    
    try:
        # 测试API连接
        test_api_connection()
        
        # 测试下单功能（dry_run）
        test_place_order_dry_run()
        
    except KeyboardInterrupt:
        print("\n\n用户中断测试")
    except Exception as e:
        print(f"\n\n测试出错: {e}")
        import traceback
        traceback.print_exc()

