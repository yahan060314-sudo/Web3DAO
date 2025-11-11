# debug_http_headers.py
import os
import hmac
import hashlib
import time
import requests
from dotenv import load_dotenv

load_dotenv()

def debug_http_headers():
    api_key = os.getenv('ROOSTOO_API_KEY')
    secret_key = os.getenv('ROOSTOO_SECRET_KEY')
    base_url = os.getenv('ROOSTOO_API_URL', 'https://mock-api.roostoo.com')
    
    timestamp = str(int(time.time() * 1000))
    endpoint = "/v3/balance"
    params = f"timestamp={timestamp}"
    
    # 生成签名
    message = timestamp + "GET" + endpoint + "?" + params
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # 测试不同的header格式
    headers_variants = [
        {
            'api-key': api_key,
            'timestamp': timestamp,
            'signature': signature,
            'Content-Type': 'application/json'
        },
        {
            'Api-Key': api_key,
            'Timestamp': timestamp,
            'Signature': signature,
            'Content-Type': 'application/json'
        },
        {
            'X-API-Key': api_key,
            'X-Timestamp': timestamp,
            'X-Signature': signature,
            'Content-Type': 'application/json'
        },
        {
            'API-KEY': api_key,
            'TIMESTAMP': timestamp,
            'SIGNATURE': signature,
            'Content-Type': 'application/json'
        }
    ]
    
    url = f"{base_url}{endpoint}?{params}"
    
    for i, headers in enumerate(headers_variants, 1):
        print(f"\n=== 测试Header格式 {i} ===")
        print(f"Headers: {headers}")
        
        try:
            # 使用Session来更详细地调试
            session = requests.Session()
            prepared = session.prepare_request(requests.Request('GET', url, headers=headers))
            
            print("实际发送的请求头:")
            for key, value in prepared.headers.items():
                print(f"  {key}: {value}")
            
            response = session.send(prepared)
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.text}")
            
            if response.status_code == 200:
                print("✓ 成功!")
                break
                
        except Exception as e:
            print(f"错误: {e}")

def test_with_curl_command():
    """生成curl命令用于手动测试"""
    api_key = os.getenv('ROOSTOO_API_KEY')
    secret_key = os.getenv('ROOSTOO_SECRET_KEY')
    base_url = os.getenv('ROOSTOO_API_URL', 'https://mock-api.roostoo.com')
    
    timestamp = str(int(time.time() * 1000))
    endpoint = "/v3/balance"
    params = f"timestamp={timestamp}"
    
    message = timestamp + "GET" + endpoint + "?" + params
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    print(f"\n=== cURL 命令 ===")
    curl_cmd = f"""curl -X GET "{base_url}{endpoint}?{params}" \\
  -H "api-key: {api_key}" \\
  -H "timestamp: {timestamp}" \\
  -H "signature: {signature}" \\
  -H "Content-Type: application/json" \\
  -v"""
    
    print(curl_cmd)

if __name__ == "__main__":
    debug_http_headers()
    test_with_curl_command()
