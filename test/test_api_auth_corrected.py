# test_api_auth_corrected.py
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
    
    # 生成签名 - 时间戳需要包含在URL和签名消息中
    timestamp = str(int(time.time() * 1000))
    
    # 正确的消息格式：timestamp + method + endpoint_with_params
    endpoint = "/v3/balance"
    query_params = f"timestamp={timestamp}"
    message = timestamp + "GET" + endpoint + "?" + query_params
    
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
    
    url = f"{base_url}{endpoint}?{query_params}"
    print(f"请求URL: {url}")
    print(f"签名消息: {message}")
    print(f"请求头: {json.dumps(headers, indent=2)}")
    
    try:
        response = requests.get(url, headers=headers)
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            print("✓ API认证成功！")
            data = response.json()
            print(f"账户余额: {json.dumps(data, indent=2)}")
            return True
        else:
            print("✗ API认证失败")
            return False
            
    except Exception as e:
        print(f"请求异常: {e}")
        return False

def test_exchange_info():
    """测试交易所信息（不需要认证）"""
    base_url = os.getenv('ROOSTOO_API_URL', 'https://mock-api.roostoo.com')
    url = f"{base_url}/v3/exchangeInfo"
    
    try:
        response = requests.get(url)
        print(f"\n交易所信息测试:")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"交易所状态: {data.get('IsRunning', 'Unknown')}")
            print(f"交易对: {list(data.get('TradePairs', {}).keys())[:3]}...")  # 只显示前3个
        else:
            print(f"响应: {response.text}")
    except Exception as e:
        print(f"交易所信息测试失败: {e}")

if __name__ == "__main__":
    test_exchange_info()
    print("\n" + "="*50)
    test_api_auth()
