# debug_auth_comparison.py
import os
import time
import hmac
import hashlib
import requests
from dotenv import load_dotenv

load_dotenv()

def debug_auth_comparison():
    api_key = os.getenv("ROOSTOO_API_KEY")
    secret_key = os.getenv("ROOSTOO_SECRET_KEY")
    base_url = "https://mock-api.roostoo.com"
    
    print("=== 认证调试比较 ===")
    print(f"API Key: {api_key}")
    print(f"Secret Key: {secret_key[:20]}...")
    
    # 获取服务器时间
    server_response = requests.get(f"{base_url}/v3/serverTime")
    server_time = server_response.json()['ServerTime']
    print(f"服务器时间: {server_time}")
    
    # 构建参数
    params = {'timestamp': str(server_time)}
    param_string = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    
    # 生成签名
    signature = hmac.new(
        secret_key.encode('utf-8'),
        param_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        'RST-API-KEY': api_key,
        'MSG-SIGNATURE': signature
    }
    
    print(f"\nPython请求详情:")
    print(f"  URL: {base_url}/v3/balance?timestamp={server_time}")
    print(f"  请求头: {headers}")
    print(f"  参数字符串: {param_string}")
    print(f"  签名: {signature}")
    
    # 发送请求
    response = requests.get(f"{base_url}/v3/balance", headers=headers, params=params)
    print(f"\n响应状态: {response.status_code}")
    print(f"响应内容: {response.text}")
    
    print(f"\nPostman等效命令:")
    print(f"curl -X GET '{base_url}/v3/balance?timestamp={server_time}' \\")
    print(f"  -H 'RST-API-KEY: {api_key}' \\")
    print(f"  -H 'MSG-SIGNATURE: {signature}'")

if __name__ == "__main__":
    debug_auth_comparison()
