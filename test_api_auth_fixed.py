# test_api_auth_fixed.py
import os
import hmac
import hashlib
import time
import requests
from dotenv import load_dotenv
import json

load_dotenv()

def test_api_auth():
    api_key = os.getenv('ROOSTOO_API_KEY')
    secret_key = os.getenv('ROOSTOO_SECRET_KEY')
    base_url = os.getenv('ROOSTOO_API_URL', 'https://mock-api.roostoo.com')
    
    print(f"API Key: {api_key[:10]}...")
    print(f"Secret Key: {secret_key[:10]}...")
    print(f"Base URL: {base_url}")
    
    # 生成签名 - 使用和实际代码相同的方法
    timestamp = str(int(time.time() * 1000))
    message = timestamp + "GET" + "/v3/balance"
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        'api-key': api_key,
        'timestamp': timestamp,
        'signature': signature,
        'Content-Type': 'application/json'
    }
    
    url = f"{base_url}/v3/balance"
    print(f"请求URL: {url}")
    print(f"请求头: {json.dumps(headers, indent=2)}")
    
    try:
        response = requests.get(url, headers=headers)
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            print("✓ API认证成功！")
            return True
        else:
            print("✗ API认证失败")
            return False
            
    except Exception as e:
        print(f"请求异常: {e}")
        return False

def test_server_time():
    """测试服务器时间端点"""
    base_url = os.getenv('ROOSTOO_API_URL', 'https://mock-api.roostoo.com')
    url = f"{base_url}/v3/time"
    
    try:
        response = requests.get(url)
        print(f"\n服务器时间测试:")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
    except Exception as e:
        print(f"服务器时间测试失败: {e}")

if __name__ == "__main__":
    test_server_time()
    print("\n" + "="*50)
    test_api_auth()
