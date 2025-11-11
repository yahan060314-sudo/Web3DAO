# debug_http_requests.py
import os
import time
import hmac
import hashlib
import requests
from dotenv import load_dotenv

load_dotenv()

def debug_http_requests():
    api_key = os.getenv("ROOSTOO_API_KEY")
    secret_key = os.getenv("ROOSTOO_SECRET_KEY")
    base_url = "https://mock-api.roostoo.com"
    
    # 获取服务器时间
    server_response = requests.get(f"{base_url}/v3/serverTime")
    server_time = server_response.json()['ServerTime']
    
    # 构建参数和签名
    params = {'timestamp': str(server_time)}
    param_string = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    
    signature = hmac.new(
        secret_key.encode('utf-8'),
        param_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # 测试不同的头格式
    header_variants = [
        # 变体1: 标准格式
        {
            'RST-API-KEY': api_key,
            'MSG-SIGNATURE': signature
        },
        # 变体2: 小写头
        {
            'rst-api-key': api_key,
            'msg-signature': signature
        },
        # 变体3: 带User-Agent
        {
            'RST-API-KEY': api_key,
            'MSG-SIGNATURE': signature,
            'User-Agent': 'Mozilla/5.0'
        },
        # 变体4: 带Content-Type
        {
            'RST-API-KEY': api_key,
            'MSG-SIGNATURE': signature,
            'Content-Type': 'application/json'
        }
    ]
    
    for i, headers in enumerate(header_variants, 1):
        print(f"\n=== 测试头格式 {i} ===")
        print(f"请求头: {headers}")
        
        # 使用Session来查看实际发送的头
        session = requests.Session()
        prepared = session.prepare_request(requests.Request(
            'GET', 
            f"{base_url}/v3/balance",
            headers=headers,
            params=params
        ))
        
        print("实际发送的请求头:")
        for key, value in prepared.headers.items():
            print(f"  {key}: {value}")
        
        try:
            response = session.send(prepared)
            print(f"响应状态: {response.status_code}")
            print(f"响应内容: {response.text}")
            
            if response.status_code == 200:
                print("✓ 成功!")
                break
        except Exception as e:
            print(f"错误: {e}")

if __name__ == "__main__":
    debug_http_requests()
