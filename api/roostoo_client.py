# roostoo_client.py (已修正)
import os
import time
import hmac
import hashlib
import requests
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# 导入频率限制器
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from utils.rate_limiter import API_RATE_LIMITER

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
    def __init__(self, api_key: str = None, secret_key: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv("ROOSTOO_API_KEY")
        self.secret_key = secret_key or os.getenv("ROOSTOO_SECRET_KEY")
        self.base_url = base_url or os.getenv("ROOSTOO_API_URL", "https://mock-api.roostoo.com")
        self.session = requests.Session()
        
        if not self.api_key or not self.secret_key:
            raise ValueError("API_KEY 或 SECRET_KEY 未设置。请检查您的 .env 文件或初始化参数。")
        
        print(f"[RoostooClient] ✓ 使用API: {self.base_url}")

    def _get_timestamp(self) -> int:
        """生成13位毫秒级时间戳整数。"""
        return int(time.time() * 1000)

    def _sign_request(self, payload: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, Any], str]:
        """
        为RCL_TopLevelCheck请求生成签名和头部。
        
        Args:
            payload (Dict[str, Any]): 请求的业务参数。

        Returns:
            Tuple[Dict[str, str], Dict[str, Any], str]: 
            一个元组，包含 (
                请求头, 
                用于GET请求的已签名参数字典, 
                用于POST请求的已签名参数字符串
            )。
        """
        timestamp = self._get_timestamp()
        signed_payload = payload.copy()
        signed_payload['timestamp'] = timestamp

        sorted_keys = sorted(signed_payload.keys())
        
        # 这个字符串既是签名内容，也是POST请求的body
        query_string = '&'.join([f"{k}={signed_payload[k]}" for k in sorted_keys])

        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        headers = {
            'RST-API-KEY': self.api_key,
            'MSG-SIGNATURE': signature
        }
        
        # signed_payload 是用于 GET 的 params
        # query_string 是用于 POST 的 data
        return headers, signed_payload, query_string

    def _request(self, method: str, path: str, timeout: Optional[float] = None, max_retries: int = 3, retry_delay: float = 1.0, **kwargs):
        """
        通用的请求发送方法，包含统一的错误处理、重试机制和频率限制。
        """
        if not API_RATE_LIMITER.can_call():
            wait_time = API_RATE_LIMITER.wait_time()
            if wait_time > 0:
                print(f"[RoostooClient] ⚠️ API调用频率限制: 需要等待 {wait_time:.1f} 秒")
                time.sleep(wait_time)
        
        API_RATE_LIMITER.record_call()
        
        url = f"{self.base_url}{path}"
        
        if timeout is None:
            timeout = 30.0
        
        print(f"[RoostooClient] 请求详情:")
        print(f"  方法: {method}")
        print(f"  URL: {url}")
        # 修正：从kwargs中获取headers, params, data
        if 'headers' in kwargs:
            # 为了安全，不打印完整的API Key和签名
            safe_headers = kwargs['headers'].copy()
            if 'RST-API-KEY' in safe_headers:
                safe_headers['RST-API-KEY'] = f"{safe_headers['RST-API-KEY'][:4]}..."
            if 'MSG-SIGNATURE' in safe_headers:
                safe_headers['MSG-SIGNATURE'] = f"{safe_headers['MSG-SIGNATURE'][:8]}..."
            print(f"  请求头: {safe_headers}")
        if 'params' in kwargs:
            print(f"  查询参数 (GET): {kwargs['params']}")
        if 'data' in kwargs:
            print(f"  请求体 (POST): {kwargs['data']}")
        
        last_exception = None
        for attempt in range(max_retries):
            try:
                # **kwargs 会自动解包 headers, params, data
                response = self.session.request(method, url, **kwargs, timeout=timeout)
                response.raise_for_status()
                print(f"[RoostooClient] ✓ 请求成功: {response.status_code}")
                return response.json()
            except requests.exceptions.HTTPError as e:
                print(f"[RoostooClient] ✗ HTTP错误: {e.response.status_code} - {e.response.reason}")
                print(f"    响应内容: {e.response.text}")
                if e.response.status_code in [401, 403, 451]:
                    raise
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
    
    def check_server_time(self) -> Dict:
        """[RCL_NoVerification] 检查服务器时间"""
        return self._request('GET', '/v3/serverTime')

    def get_exchange_info(self) -> Dict:
        """[RCL_NoVerification] 获取交易所信息"""
        return self._request('GET', '/v3/exchangeInfo')

    def get_ticker(self, pair: str = None) -> Dict:
        """[RCL_TSCheck] 获取市场行情"""
        params = {'timestamp': self._get_timestamp()}
        if pair:
            params['pair'] = pair
        return self._request('GET', '/v3/ticker', params=params)

    def get_balance(self, timeout: Optional[float] = None) -> Dict:
        """
        [RCL_TopLevelCheck] 获取账户余额信息 (已修正)
        """
        # 修正: 遵循官方示例，使用 params=dictionary 的方式
        headers, signed_params, _ = self._sign_request({})
        return self._request('GET', '/v3/balance', headers=headers, params=signed_params, timeout=timeout)

    def get_pending_count(self, timeout: Optional[float] = None) -> Dict:
        """
        [RCL_TopLevelCheck] 获取挂单数量 (已修正)
        """
        # 修正: 遵循官方示例，使用 params=dictionary 的方式
        headers, signed_params, _ = self._sign_request({})
        return self._request('GET', '/v3/pending_count', headers=headers, params=signed_params, timeout=timeout)

    def place_order(self, pair: str, side: str, quantity: float, price: Optional[float] = None) -> Dict:
        """
        [RCL_TopLevelCheck] 下新订单（市价或限价） (实现正确，无需修改)
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
        
        # 对于POST，使用签名生成的字符串作为data是正确的
        headers, _, data_string = self._sign_request(payload)
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        return self._request('POST', '/v3/place_order', headers=headers, data=data_string)

    def query_order(self, order_id: Optional[str] = None, pair: Optional[str] = None) -> Dict:
        """[RCL_TopLevelCheck] 查询订单 (实现正确，无需修改)"""
        payload = {}
        if order_id:
            payload['order_id'] = order_id
        elif pair:
            payload['pair'] = pair
            
        headers, _, data_string = self._sign_request(payload)
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        return self._request('POST', '/v3/query_order', headers=headers, data=data_string)

    def cancel_order(self, order_id: Optional[str] = None, pair: Optional[str] = None) -> Dict:
        """[RCL_TopLevelCheck] 取消订单 (实现正确，无需修改)"""
        payload = {}
        if order_id:
            payload['order_id'] = order_id
        elif pair:
            payload['pair'] = pair
            
        headers, _, data_string = self._sign_request(payload)
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        return self._request('POST', '/v3/cancel_order', headers=headers, data=data_string)
