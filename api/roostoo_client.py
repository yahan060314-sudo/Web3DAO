# roostoo_client.py
import os
import time
import hmac
import hashlib
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class RoostooClient:
    def __init__(self, api_key: str = None, secret_key: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv("ROOSTOO_API_KEY")
        self.secret_key = secret_key or os.getenv("ROOSTOO_SECRET_KEY")
        self.base_url = base_url or os.getenv("ROOSTOO_API_URL", "https://mock-api.roostoo.com")
        self.session = requests.Session()
        
        # 初始化时间偏移
        self.time_offset = 0
        self._sync_time()

    def _sync_time(self):
        """同步服务器时间"""
        try:
            response = self.session.get(f"{self.base_url}/v3/serverTime", timeout=10)
            server_time = response.json()['ServerTime']
            local_time = int(time.time() * 1000)
            self.time_offset = server_time - local_time
            print(f"[RoostooClient] 时间同步: 偏移 {self.time_offset}ms")
        except Exception as e:
            print(f"[RoostooClient] 时间同步失败，使用本地时间: {e}")
            self.time_offset = 0

    def _get_synchronized_timestamp(self) -> str:
        """获取与服务器同步的时间戳"""
        local_time = int(time.time() * 1000)
        synchronized_time = local_time + self.time_offset
        return str(synchronized_time)

    def _generate_signature(self, param_string: str) -> str:
        """生成HMAC SHA256签名"""
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            param_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _build_param_string(self, params: Dict[str, Any]) -> str:
        """构建参数字符串（按字母顺序排序）"""
        sorted_params = sorted(params.items())
        param_string = "&".join(f"{k}={v}" for k, v in sorted_params)
        return param_string

    def get_balance(self) -> Dict:
        """获取账户余额"""
        # 每次请求前重新同步时间（可选，为了更精确）
        self._sync_time()
        
        timestamp = self._get_synchronized_timestamp()
        params = {'timestamp': timestamp}
        
        param_string = self._build_param_string(params)
        signature = self._generate_signature(param_string)
        
        headers = {
            'RST-API-KEY': self.api_key,
            'MSG-SIGNATURE': signature
        }
        
        print(f"[RoostooClient] 余额请求:")
        print(f"  时间戳: {timestamp}")
        print(f"  参数字符串: {param_string}")
        print(f"  签名: {signature}")
        
        url = f"{self.base_url}/v3/balance"
        response = self.session.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            print("[RoostooClient] ✓ 余额请求成功")
        else:
            print(f"[RoostooClient] ✗ 余额请求失败: {response.status_code} - {response.text}")
            
        return response.json()

    def get_ticker(self, pair: str = None) -> Dict:
        """获取市场行情"""
        timestamp = self._get_synchronized_timestamp()
        params = {'timestamp': timestamp}
        if pair:
            params['pair'] = pair
            
        url = f"{self.base_url}/v3/ticker"
        response = self.session.get(url, params=params, timeout=10)
        return response.json()

    def get_exchange_info(self) -> Dict:
        """获取交易所信息"""
        url = f"{self.base_url}/v3/exchangeInfo"
        response = self.session.get(url, timeout=10)
        return response.json()

# 测试修复的客户端
def test_fixed_client():
    client = RoostooClient()
    
    print("=== 测试修复的Roostoo客户端 ===")
    
    try:
        # 测试余额
        print("\n1. 测试余额查询...")
        balance = client.get_balance()
        print(f"余额响应: {balance}")
        
        # 测试市场数据
        print("\n2. 测试市场行情...")
        ticker = client.get_ticker("BTC/USD")
        print(f"BTC/USD行情: {ticker}")
        
        # 测试交易所信息
        print("\n3. 测试交易所信息...")
        exchange_info = client.get_exchange_info()
        print(f"交易所状态: {exchange_info.get('IsRunning', 'Unknown')}")
        
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == "__main__":
    test_fixed_client()
