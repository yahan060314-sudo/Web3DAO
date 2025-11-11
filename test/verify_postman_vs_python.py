# verify_postman_vs_python.py
import os
import hmac
import hashlib
import requests
from dotenv import load_dotenv

load_dotenv()

def verify_differences():
    """验证Postman和Python之间的差异"""
    
    # 从环境变量获取
    py_api_key = os.getenv("ROOSTOO_API_KEY")
    py_secret_key = os.getenv("ROOSTOO_SECRET_KEY")
    
    # 这是您在Postman中使用的值（请确认）
    postman_api_key = "K9IL3ZxCV1bN5mQwE7rT0yUiP2oA8sDdF6gJ1hKIZ4xC9vBnM0qW3eRtY5ul7oPa"
    postman_secret_key = "cV2bN4mQwE6rT8yUiP0oA9sDdF1gJ2hK3L4M5N6O7P8Q9R0S1T2U3V4W5X6Y7Z8"
    
    print("=== API Key 比较 ===")
    print(f"Python API Key: '{py_api_key}'")
    print(f"Postman API Key: '{postman_api_key}'")
    print(f"相同: {py_api_key == postman_api_key}")
    print(f"长度 - Python: {len(py_api_key)}, Postman: {len(postman_api_key)}")
    
    print("\n=== Secret Key 比较 ===")
    print(f"Python Secret Key: '{py_secret_key[:20]}...'")
    print(f"Postman Secret Key: '{postman_secret_key[:20]}...'")
    print(f"相同: {py_secret_key == postman_secret_key}")
    print(f"长度 - Python: {len(py_secret_key)}, Postman: {len(postman_secret_key)}")
    
    # 检查字符差异
    if py_api_key != postman_api_key:
        print("\n=== API Key 字符差异 ===")
        for i, (py_char, pm_char) in enumerate(zip(py_api_key, postman_api_key)):
            if py_char != pm_char:
                print(f"位置 {i}: Python '{py_char}' (ASCII {ord(py_char)}) vs Postman '{pm_char}' (ASCII {ord(pm_char)})")
    
    # 使用Postman的值测试
    print("\n=== 使用Postman的值测试 ===")
    base_url = "https://mock-api.roostoo.com"
    server_response = requests.get(f"{base_url}/v3/serverTime")
    server_time = server_response.json()['ServerTime']
    
    params = {'timestamp': str(server_time)}
    param_string = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    
    # 使用Postman的secret key生成签名
    signature = hmac.new(
        postman_secret_key.encode('utf-8'),
        param_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        'RST-API-KEY': postman_api_key,
        'MSG-SIGNATURE': signature
    }
    
    response = requests.get(f"{base_url}/v3/balance", headers=headers, params=params)
    print(f"使用Postman值的响应: {response.status_code} - {response.text}")

if __name__ == "__main__":
    verify_differences()
