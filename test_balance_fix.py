#!/usr/bin/env python3
"""
测试余额接口修复
"""
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from api.roostoo_client import RoostooClient

def test_balance():
    """测试余额接口"""
    print("=" * 60)
    print("测试余额接口")
    print("=" * 60)
    
    # 检查环境变量
    api_key = os.getenv("ROOSTOO_API_KEY")
    secret_key = os.getenv("ROOSTOO_SECRET_KEY")
    api_url = os.getenv("ROOSTOO_API_URL", "https://mock-api.roostoo.com")
    
    print(f"\n环境变量检查:")
    print(f"  ROOSTOO_API_KEY: {'✓ 已配置 (' + api_key[:10] + '...)' if api_key else '✗ 未配置'}")
    print(f"  ROOSTOO_SECRET_KEY: {'✓ 已配置' if secret_key else '✗ 未配置'}")
    print(f"  ROOSTOO_API_URL: {api_url}")
    
    # 创建客户端
    print(f"\n创建RoostooClient...")
    try:
        client = RoostooClient()
        print(f"  ✓ 客户端创建成功")
        print(f"  使用的API Key: {client.api_key[:15] + '...' if len(client.api_key) > 15 else client.api_key}")
        print(f"  使用的Secret Key: {'已设置 (' + str(len(client.secret_key)) + ' 字符)' if client.secret_key else '未设置'}")
        print(f"  使用的URL: {client.base_url}")
        
        # 测试获取余额
        print(f"\n测试获取余额...")
        try:
            balance = client.get_balance(timeout=30.0)
            print(f"  ✓ 余额获取成功!")
            print(f"  响应键: {list(balance.keys())[:5]}")
            if 'data' in balance:
                data = balance['data']
                if 'SpotWallet' in data:
                    print(f"  ✓ 找到SpotWallet数据")
                    spot_wallet = data['SpotWallet']
                    print(f"  币种: {list(spot_wallet.keys())}")
                else:
                    print(f"  响应数据: {str(data)[:200]}")
            return True
        except Exception as e:
            print(f"  ✗ 余额获取失败: {e}")
            print(f"\n可能的原因:")
            print(f"  1. API凭证无效")
            print(f"  2. Mock API需要有效的API凭证")
            print(f"  3. API服务器返回错误")
            return False
    except Exception as e:
        print(f"  ✗ 客户端创建失败: {e}")
        return False

if __name__ == "__main__":
    success = test_balance()
    sys.exit(0 if success else 1)

