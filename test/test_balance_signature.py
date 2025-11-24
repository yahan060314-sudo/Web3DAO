#!/usr/bin/env python3
"""
测试余额API的签名生成
用于诊断401错误
"""
import os
import sys
import time
import hmac
import hashlib
from pathlib import Path
from urllib.parse import urlencode
from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

load_dotenv()

from api.roostoo_client import RoostooClient

def test_signature_generation():
    """测试签名生成过程"""
    print("=" * 80)
    print("测试签名生成")
    print("=" * 80)
    print()
    
    client = RoostooClient()
    
    # 1. 获取时间戳
    timestamp = client._get_timestamp()
    print(f"1. 时间戳: {timestamp}")
    
    # 2. 构建payload
    payload = {}
    payload['timestamp'] = timestamp
    print(f"2. Payload: {payload}")
    
    # 3. 排序参数
    sorted_payload = sorted(payload.items())
    print(f"3. 排序后的参数: {sorted_payload}")
    
    # 4. 拼接参数字符串
    total_params = urlencode(sorted_payload)
    print(f"4. 参数字符串: {total_params}")
    
    # 5. 生成签名
    signature = hmac.new(
        client.secret_key.encode('utf-8'),
        total_params.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    print(f"5. 签名: {signature}")
    
    # 6. 构建请求头
    headers = {
        'RST-API-KEY': client.api_key,
        'MSG-SIGNATURE': signature
    }
    print(f"6. 请求头:")
    print(f"   RST-API-KEY: {client.api_key[:20]}...")
    print(f"   MSG-SIGNATURE: {signature[:40]}...")
    
    print()
    print("=" * 80)
    print("测试实际调用")
    print("=" * 80)
    print()
    
    # 7. 测试实际调用
    try:
        print(f"调用 get_balance()...")
        print(f"  API URL: {client.base_url}")
        print(f"  URL参数: timestamp={timestamp}")
        print()
        
        balance = client.get_balance()
        print(f"✓ 成功获取余额: {balance}")
        return True
    except Exception as e:
        print(f"✗ 调用失败: {e}")
        print()
        print("可能的原因:")
        print("  1. Mock API不接受真实的API Key")
        print("  2. Mock API的认证方式不同")
        print("  3. API Key或Secret Key不正确")
        print("  4. 需要使用真实的API URL而不是mock API")
        return False

def test_with_different_timestamps():
    """测试时间戳一致性"""
    print()
    print("=" * 80)
    print("测试时间戳一致性")
    print("=" * 80)
    print()
    
    client = RoostooClient()
    
    # 测试1: 使用相同时间戳
    print("测试1: 使用相同时间戳（正确方式）")
    headers1, _, timestamp1 = client._sign_request({})
    print(f"  签名时时间戳: {timestamp1}")
    print(f"  请求时时间戳: {timestamp1}")
    print(f"  ✓ 时间戳一致")
    
    # 测试2: 使用不同时间戳（错误方式）
    print()
    print("测试2: 使用不同时间戳（错误方式）")
    headers2, _, timestamp2 = client._sign_request({})
    timestamp3 = client._get_timestamp()  # 新时间戳
    print(f"  签名时时间戳: {timestamp2}")
    print(f"  请求时时间戳: {timestamp3}")
    print(f"  ⚠️ 时间戳不一致（这会导致签名验证失败）")
    
    print()
    print("=" * 80)
    print("结论")
    print("=" * 80)
    print()
    print("如果代码修复正确，签名时和请求时应该使用相同的时间戳。")
    print("如果仍然出现401错误，可能是:")
    print("  1. Mock API不接受真实的API Key")
    print("  2. 需要使用真实的API URL")

if __name__ == "__main__":
    try:
        # 测试签名生成
        success = test_signature_generation()
        
        # 测试时间戳一致性
        test_with_different_timestamps()
        
        if not success:
            print()
            print("=" * 80)
            print("建议")
            print("=" * 80)
            print()
            print("如果Mock API不接受真实的API Key，可以:")
            print("  1. 使用真实的API URL（如果比赛已开始）")
            print("  2. 或者跳过余额获取测试（其他功能正常）")
            print("  3. 或者联系比赛组织者获取Mock API的测试API Key")
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

