# check_api_key_validity.py
import requests

def check_api_key_validity():
    """检查API密钥是否有效"""
    base_url = "https://mock-api.roostoo.com"
    
    # 测试不同的API密钥格式
    test_cases = [
        {
            "name": "当前API密钥",
            "api_key": "K9IL3ZxCV1bN5mQwE7rT0yUiP2oA8sDdF6gJ1hKIZ4xC9vBnM0qW3eRtY5ul7oPa",
            "secret_key": "cV2bN4mQwE6rT8yUiP0oA9sDdF1gJ2hK3L4M5N6O7P8Q9R0S1T2U3V4W5X6Y7Z8"
        },
        {
            "name": "测试其他可能格式",
            "api_key": "K9IL3ZxCV1bN5mQwE7rT0yUiP2oA8sDdF6gJ1hKIZ4xC9vBnM0qW3eRtY5ul7oPa",
            "secret_key": "cV2bN4mQwE6rT8yUiP0oA9sDdF1gJ2hK3L4M5N6O7P8Q9R0S1T2U3V4W5X6Y7Z8aBcD"
        }
    ]
    
    for test in test_cases:
        print(f"\n=== 测试: {test['name']} ===")
        print(f"API Key: {test['api_key'][:20]}...")
        print(f"Secret Key: {test['secret_key'][:20]}...")
        
        # 获取服务器时间
        try:
            server_response = requests.get(f"{base_url}/v3/serverTime")
            server_time = server_response.json()['ServerTime']
            
            # 构建请求
            params = {'timestamp': str(server_time)}
            param_string = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            
            # 生成签名
            import hmac
            import hashlib
            signature = hmac.new(
                test['secret_key'].encode('utf-8'),
                param_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            headers = {
                'RST-API-KEY': test['api_key'],
                'MSG-SIGNATURE': signature
            }
            
            response = requests.get(f"{base_url}/v3/balance", headers=headers, params=params)
            print(f"响应状态: {response.status_code}")
            print(f"响应内容: {response.text}")
            
        except Exception as e:
            print(f"请求异常: {e}")

if __name__ == "__main__":
    check_api_key_validity()
