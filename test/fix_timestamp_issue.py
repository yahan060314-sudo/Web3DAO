# fix_timestamp_issue.py
import os
import hmac
import hashlib
import time
import requests
from dotenv import load_dotenv
import json

load_dotenv()

def get_server_time():
    """获取服务器时间"""
    base_url = os.getenv('ROOSTOO_API_URL', 'https://mock-api.roostoo.com')
    url = f"{base_url}/v3/time"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            server_time = data.get('ServerTime')
            print(f"服务器时间: {server_time}")
            print(f"本地时间: {int(time.time() * 1000)}")
            return server_time
        else:
            print(f"获取服务器时间失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"获取服务器时间异常: {e}")
        return None

def test_with_server_time():
    """使用服务器时间进行认证测试"""
    api_key = os.getenv('ROOSTOO_API_KEY')
    secret_key = os.getenv('ROOSTOO_SECRET_KEY')
    base_url = os.getenv('ROOSTOO_API_URL', 'https://mock-api.roostoo.com')
    
    # 1. 先获取服务器时间
    server_time = get_server_time()
    if not server_time:
        print("无法获取服务器时间，使用本地时间")
        server_time = int(time.time() * 1000)
    
    timestamp = str(server_time)
    
    # 2. 生成签名
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
    print(f"\n请求URL: {url}")
    print(f"签名消息: {message}")
    print(f"签名: {signature}")
    
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

def test_time_sync():
    """测试时间同步"""
    base_url = os.getenv('ROOSTOO_API_URL', 'https://mock-api.roostoo.com')
    
    for i in range(3):
        print(f"\n--- 测试 {i+1} ---")
        server_time = get_server_time()
        if server_time:
            local_time = int(time.time() * 1000)
            time_diff = abs(server_time - local_time) / 1000  # 转换为秒
            print(f"时间差: {time_diff:.2f} 秒")
            
            if time_diff > 60:
                print("⚠️ 时间差超过60秒，需要同步系统时间")
            else:
                print("✓ 时间同步正常")
        time.sleep(1)

if __name__ == "__main__":
    print("=== 时间同步测试 ===")
    test_time_sync()
    
    print("\n=== 使用服务器时间认证测试 ===")
    test_with_server_time()
