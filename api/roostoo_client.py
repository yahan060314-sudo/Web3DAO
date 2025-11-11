# roostoo_client.py

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

    def _get_timestamp(self) -> int:
        """生成13位毫秒级时间戳整数（与官方示例保持一致）。"""
        return int(time.time() * 1000)

    def _sign_request(self, payload: Dict[str, Any]) -> Tuple[Dict[str, str], str, int]:
        """
        为RCL_TopLevelCheck请求生成签名和头部。
        严格遵循官方文档中的签名规则，与官方python_demo.py保持一致。

        Args:
            payload (Dict[str, Any]): 请求的业务参数。

        Returns:
            Tuple[Dict[str, str], str, int]: 一个元组，包含(请求头, 用于POST data的参数字符串, 时间戳整数)。
        """
        # 1. 添加时间戳（整数，与官方示例保持一致）
        timestamp = self._get_timestamp()
        # 创建新的字典，避免修改原始payload
        signed_payload = payload.copy()
        signed_payload['timestamp'] = timestamp

        # 2. 按照key的字母顺序排序参数（与官方示例完全一致）
        # 官方示例: query_string = '&'.join(["{}={}".format(k, params[k]) for k in sorted(params.keys())])
        sorted_keys = sorted(signed_payload.keys())
        
        # 3. 拼接成 "key1=value1&key2=value2" 格式的字符串
        # 使用与官方示例完全相同的格式: format会将整数自动转换为字符串
        # 例如: timestamp=1580774512000
        query_string = '&'.join(["{}={}".format(k, signed_payload[k]) for k in sorted_keys])

        # 4. 使用HMAC-SHA256算法生成签名（与官方示例完全一致）
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # 5. 构建请求头
        headers = {
            'RST-API-KEY': self.api_key,
            'MSG-SIGNATURE': signature
        }
        
        return headers, query_string, timestamp

    def _request(self, method: str, path: str, timeout: Optional[float] = None, max_retries: int = 3, retry_delay: float = 1.0, **kwargs):
        """
        通用的请求发送方法，包含统一的错误处理和重试机制。
        包含API调用频率限制（每分钟最多5次）。

        Args:
            method (str): HTTP方法 (GET, POST)。
            path (str): API端点路径。
            timeout (float, optional): 请求超时时间（秒）。如果为None，使用默认值30秒。
            max_retries (int): 最大重试次数，默认3次。
            retry_delay (float): 重试延迟时间（秒），默认1秒。
            **kwargs: 传递给 requests 的其他参数 (headers, params, data)。
        
        Returns:
            Dict: API返回的JSON数据。
        """
        # API调用频率限制：每分钟最多5次
        if not API_RATE_LIMITER.can_call():
            wait_time = API_RATE_LIMITER.wait_time()
            if wait_time > 0:
                print(f"[RoostooClient] ⚠️ API调用频率限制: 需要等待 {wait_time:.1f} 秒")
                time.sleep(wait_time)
        
        # 记录API调用
        API_RATE_LIMITER.record_call()
        
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
        """
        [RCL_TopLevelCheck] 获取账户余额信息
        
        重要: 对于GET请求，必须使用签名时生成的参数，确保服务器验证签名时使用的查询字符串
        和签名时使用的完全一致。与官方python_demo.py的实现保持一致。
        """
        # 生成签名（与官方示例完全一致）
        # _sign_request会在内部添加timestamp，确保签名和请求使用相同的时间戳
        headers, query_string, _ = self._sign_request({})
        
        # 对于GET请求，直接使用签名时生成的query_string拼接到URL
        # 确保服务器验证签名时使用的查询字符串和签名时使用的完全一致
        return self._request('GET', f'/v3/balance?{query_string}', headers=headers, timeout=timeout)

    def get_pending_count(self, timeout: Optional[float] = None) -> Dict:
        """
        [RCL_TopLevelCheck] 获取挂单数量
        
        重要: 对于GET请求，必须使用签名时生成的参数，确保服务器验证签名时使用的查询字符串
        和签名时使用的完全一致。与官方python_demo.py的实现保持一致。
        """
        # 生成签名（与官方示例完全一致）
        headers, query_string, _ = self._sign_request({})
        
        # 对于GET请求，直接使用签名时生成的query_string拼接到URL
        return self._request('GET', f'/v3/pending_count?{query_string}', headers=headers, timeout=timeout)

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
            payload['type'] = 'LIMIT'  # 修复: 使用 'type' 而不是 'order_type'
            payload['price'] = str(price)
        else:
            payload['type'] = 'MARKET'  # 修复: 使用 'type' 而不是 'order_type'
        
        headers, data_string, _ = self._sign_request(payload)
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        return self._request('POST', '/v3/place_order', headers=headers, data=data_string)

    def query_order(self, order_id: Optional[str] = None, pair: Optional[str] = None) -> Dict:
        """[RCL_TopLevelCheck] 查询订单"""
        payload = {}
        if order_id:
            payload['order_id'] = order_id
        elif pair:
            payload['pair'] = pair
            
        headers, data_string, _ = self._sign_request(payload)
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        return self._request('POST', '/v3/query_order', headers=headers, data=data_string)

    def cancel_order(self, order_id: Optional[str] = None, pair: Optional[str] = None) -> Dict:
        """[RCL_TopLevelCheck] 取消订单"""
        payload = {}
        if order_id:
            payload['order_id'] = order_id
        elif pair:
            payload['pair'] = pair
            
        headers, data_string, _ = self._sign_request(payload)
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        return self._request('POST', '/v3/cancel_order', headers=headers, data=data_string)