# test_api_auth.py
import os
import hmac
import hashlib
import time
import requests
from dotenv import load_dotenv

load_dotenv()

def test_api_auth():
    api_key = os.getenv('ROOSTOO_API_KEY')
    secret_key = os.getenv('ROOSTOO_SECRET_KEY')
    base_url = os.getenv('ROOSTOO_API_URL', 'https://mock-api.roostoo.com')
    
    print(f"API Key: {api_key[:10]}...")
    print(f"Secret Key: {secret_key[:10]}...")
    print(f"Base URL: {base_url}")
    
    # 生成签名
    timestamp = str(int(time.time() * 1000))
    message = f"{timestamp}GET/v3/balance"
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        'api-key': api_key,
        'timestamp': timestamp,
        'signature': signature
    }
    
    url = f"{base_url}/v3/balance?timestamp={timestamp}"
    print(f"请求URL: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        print(f"状态码: {response.status_code}")
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

if __name__ == "__main__":
    test_api_auth()
