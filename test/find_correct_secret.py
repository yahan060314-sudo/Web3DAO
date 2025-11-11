# find_correct_secret.py
import os
import hmac
import hashlib
import requests
from dotenv import load_dotenv

load_dotenv()

def test_different_secrets():
    base_url = "https://mock-api.roostoo.com"
    
    # 获取服务器时间
    server_response = requests.get(f"{base_url}/v3/serverTime")
    server_time = server_response.json()['ServerTime']
    
    api_key = "K9IL3ZxCV1bN5mQwE7rT0yUiP2oA8sDdF6gJ1hKIZ4xC9vBnM0qW3eRtY5ul7oPa"
    
    # 测试不同的Secret Key格式
    test_secrets = [
        # 当前环境变量的值
        os.getenv("ROOSTOO_SECRET_KEY"),
        # 可能的64字符版本（在末尾添加字符）
        os.getenv("ROOSTOO_SECRET_KEY") + "ABC",  # 如果当前是61字符
        os.getenv("ROOSTOO_SECRET_KEY") + "ABCD", # 如果当前是60字符  
        # 可能的正确值（您需要确认）
        "cV2bN4mQwE6rT8yUiP0oA9sDdF1gJ2hK3L4M5N6O7P8Q9R0S1T2U3V4W5X6Y7Z8aBcD",
    ]
    
    params = {'timestamp': str(server_time)}
    param_string = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    
    for i, secret in enumerate(test_secrets):
        if not secret:
            continue
            
        print(f"\n=== 测试 Secret Key {i+1} ===")
        print(f"Secret Key: {secret[:20]}...")
        print(f"长度: {len(secret)}")
        
        try:
            signature = hmac.new(
                secret.encode('utf-8'),
                param_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            headers = {
                'RST-API-KEY': api_key,
                'MSG-SIGNATURE': signature
            }
            
            response = requests.get(f"{base_url}/v3/balance", headers=headers, params=params)
            print(f"响应: {response.status_code}")
            
            if response.status_code == 200:
                print("🎉 找到正确的Secret Key!")
                print(f"正确的Secret Key: {secret}")
                print(f"响应内容: {response.text}")
                return secret
            else:
                print(f"错误: {response.text}")
                
        except Exception as e:
            print(f"异常: {e}")
    
    print("\n❌ 没有找到正确的Secret Key")
    return None

if __name__ == "__main__":
    correct_secret = test_different_secrets()
    if correct_secret:
        print(f"\n请更新.env文件中的ROOSTOO_SECRET_KEY为: {correct_secret}")
