# roostoo_client.py

import os
import time
import hmac
import hashlib
import requests
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ROOSTOO_API_KEY")
SECRET_KEY = os.getenv("ROOSTOO_SECRET_KEY")

ROOSTOO_API_URL = os.getenv("ROOSTOO_API_URL")
if not ROOSTOO_API_URL:
    raise ValueError(
        "ROOSTOO_API_URL未在.env文件中设置。\n"
        "请在.env文件中设置: ROOSTOO_API_URL=https://mock-api.roostoo.com"
    )
BASE_URL = ROOSTOO_API_URL

class RoostooClient:
    """
    Roostoo API的Python客户端，完全按照官方文档实现认证逻辑。
    """
    def __init__(self, api_key: str = API_KEY, secret_key: str = SECRET_KEY, base_url: str = None):
        if not api_key or not secret_key:
            raise ValueError("API Key和Secret Key不能为空。请检查您的.env文件或初始化参数。")
        
        self.base_url = base_url or BASE_URL
        self.api_key = api_key
        self.secret_key = secret_key
        self.session = requests.Session()
        
        print(f"[RoostooClient] ✓ 使用API: {self.base_url}")

    def _get_timestamp(self) -> str:
        """生成13位毫秒级时间戳字符串。"""
        return str(int(time.time() * 1000))

    def _generate_signature(self, param_string: str) -> str:
        """
        生成HMAC SHA256签名。
        
        Args:
            param_string: 参数字符串（GET的查询字符串或POST的请求体）
            
        Returns:
            HMAC SHA256签名
        """
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            param_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature

    def _build_param_string(self, params: Dict[str, Any]) -> str:
        """
        构建参数字符串（按字母顺序排序）。
        
        Args:
            params: 参数字典
            
        Returns:
            排序后的参数字符串
        """
        sorted_params = sorted(params.items())
        param_string = "&".join(f"{k}={v}" for k, v in sorted_params)
        return param_string

    def _request(self, method: str, path: str, timeout: Optional[float] = None, max_retries: int = 3, retry_delay: float = 1.0, **kwargs):
        """
        通用的请求发送方法。
        """
        url = f"{self.base_url}{path}"
        
        if timeout is None:
            timeout = 30.0
        
        # 打印请求详情用于调试
        print(f"[RoostooClient] 请求详情:")
        print(f"  方法: {method}")
        print(f"  URL: {url}")
        if 'headers' in kwargs:
            print(f"  请求头: {kwargs['headers']}")
        if 'params' in kwargs:
            print(f"  查询参数: {kwargs['params']}")
        if 'data' in kwargs:
            print(f"  POST数据: {kwargs['data']}")
        
        last_exception = None
        for attempt in range(max_retries):
            try:
                response = self.session.request(method, url, **kwargs, timeout=timeout)
                response.raise_for_status()
                print(f"[RoostooClient] ✓ 请求成功: {response.status_code}")
                return response.json()
            except requests.exceptions.HTTPError as e:
                print(f"[RoostooClient] ✗ HTTP错误: {e.response.status_code} - {e.response.reason}")
                print(f"    响应内容: {e.response.text}")
                # 对于认证错误，直接抛出，不需要重试
                if e.response.status_code in [401, 403, 451]:
                    raise
                # 其他HTTP错误可以重试
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    print(f"[RoostooClient] ⚠️ HTTP错误 (尝试 {attempt + 1}/{max_retries})，{wait_time:.1f}秒后重试...")
                    time.sleep(wait_time)
                else:
                    raise
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    print(f"[RoostooClient] ⚠️ 请求异常 (尝试 {attempt + 1}/{max_retries})，{wait_time:.1f}秒后重试...")
                    time.sleep(wait_time)
                else:
                    raise
        
        if last_exception:
            raise last_exception

    # --- Public API Endpoints ---

    def check_server_time(self, timeout: Optional[float] = None) -> Dict:
        """[RCL_NoVerification] 检查服务器时间"""
        return self._request('GET', '/v3/serverTime', timeout=timeout)

    def get_exchange_info(self, timeout: Optional[float] = None) -> Dict:
        """[RCL_NoVerification] 获取交易所信息，包括交易对、精度等"""
        return self._request('GET', '/v3/exchangeInfo', timeout=timeout)

    def get_ticker(self, pair: Optional[str] = None, timeout: Optional[float] = None) -> Dict:
        """[RCL_TSCheck] 获取市场Ticker信息"""
        # RCL_TSCheck只需要timestamp参数，不需要签名
        timestamp = self._get_timestamp()
        params = {'timestamp': timestamp}
        if pair:
            params['pair'] = pair
        return self._request('GET', '/v3/ticker', params=params, timeout=timeout)

    def get_balance(self, timeout: Optional[float] = None) -> Dict:
        """[RCL_TopLevelCheck] 获取账户余额信息"""
        # 关键修正：GET请求的签名基于完整的查询字符串
        timestamp = self._get_timestamp()
        params = {'timestamp': timestamp}
        
        # 构建查询字符串（按字母顺序排序）
        param_string = self._build_param_string(params)
        
        # 生成签名（基于完整的查询字符串）
        signature = self._generate_signature(param_string)
        
        headers = {
            'RST-API-KEY': self.api_key,
            'MSG-SIGNATURE': signature
        }
        
        print(f"[RoostooClient] 余额请求签名调试:")
        print(f"  参数字符串: {param_string}")
        print(f"  签名: {signature}")
        print(f"  请求头: {headers}")
        
        return self._request('GET', '/v3/balance', headers=headers, params=params, timeout=timeout)

    def get_pending_count(self, timeout: Optional[float] = None) -> Dict:
        """[RCL_TopLevelCheck] 获取挂单数量"""
        timestamp = self._get_timestamp()
        params = {'timestamp': timestamp}
        
        param_string = self._build_param_string(params)
        signature = self._generate_signature(param_string)
        
        headers = {
            'RST-API-KEY': self.api_key,
            'MSG-SIGNATURE': signature
        }
        
        return self._request('GET', '/v3/pending_count', headers=headers, params=params, timeout=timeout)

    def place_order(self, pair: str, side: str, quantity: float, price: Optional[float] = None) -> Dict:
        """
        [RCL_TopLevelCheck] 下新订单（市价或限价）
        """
        payload = {
            'pair': pair,
            'side': side.upper(),
            'quantity': str(quantity),
        }
        if price is not None:
            payload['type'] = 'LIMIT'
            payload['price'] = str(price)
        else:
            payload['type'] = 'MARKET'
        
        # 添加时间戳
        payload['timestamp'] = self._get_timestamp()
        
        # 构建参数字符串（按字母顺序排序）
        param_string = self._build_param_string(payload)
        
        # 生成签名（基于请求体字符串）
        signature = self._generate_signature(param_string)
        
        headers = {
            'RST-API-KEY': self.api_key,
            'MSG-SIGNATURE': signature,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        print(f"[RoostooClient] 下单请求签名调试:")
        print(f"  参数字符串: {param_string}")
        print(f"  签名: {signature}")
        print(f"  请求头: {headers}")
        
        return self._request('POST', '/v3/place_order', headers=headers, data=param_string)

    def query_order(self, order_id: Optional[str] = None, pair: Optional[str] = None) -> Dict:
        """[RCL_TopLevelCheck] 查询订单"""
        payload = {}
        if order_id:
            payload['order_id'] = order_id
        elif pair:
            payload['pair'] = pair
            
        # 添加时间戳
        payload['timestamp'] = self._get_timestamp()
        
        param_string = self._build_param_string(payload)
        signature = self._generate_signature(param_string)
        
        headers = {
            'RST-API-KEY': self.api_key,
            'MSG-SIGNATURE': signature,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        return self._request('POST', '/v3/query_order', headers=headers, data=param_string)

    def cancel_order(self, order_id: Optional[str] = None, pair: Optional[str] = None) -> Dict:
        """[RCL_TopLevelCheck] 取消订单"""
        payload = {}
        if order_id:
            payload['order_id'] = order_id
        elif pair:
            payload['pair'] = pair
            
        # 添加时间戳
        payload['timestamp'] = self._get_timestamp()
        
        param_string = self._build_param_string(payload)
        signature = self._generate_signature(param_string)
        
        headers = {
            'RST-API-KEY': self.api_key,
            'MSG-SIGNATURE': signature,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        return self._request('POST', '/v3/cancel_order', headers=headers, data=param_string)


# 测试函数
def test_client():
    """测试修正后的客户端"""
    try:
        client = RoostooClient()
        
        print("\n=== 测试开始 ===")
        
        # 测试服务器时间
        print("\n1. 测试服务器时间...")
        server_time = client.check_server_time()
        print(f"   服务器时间: {server_time}")
        
        # 测试交易所信息
        print("\n2. 测试交易所信息...")
        exchange_info = client.get_exchange_info()
        print(f"   交易所状态: {exchange_info.get('IsRunning', 'Unknown')}")
        pairs = list(exchange_info.get('TradePairs', {}).keys())[:3]
        print(f"   前3个交易对: {pairs}")
        
        # 测试市场行情
        print("\n3. 测试市场行情...")
        ticker = client.get_ticker("BTC/USD")
        btc_data = ticker.get('Data', {}).get('BTC/USD', {})
        print(f"   BTC/USD最新价: {btc_data.get('LastPrice', 'Unknown')}")
        
        # 测试账户余额
        print("\n4. 测试账户余额...")
        balance = client.get_balance()
        print(f"   余额响应: {balance}")
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"\n=== 测试失败 ===")
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_client()
