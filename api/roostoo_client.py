# roostoo_client.py

import os
import time
import hmac
import hashlib
import requests
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode

# 假设您的项目结构中有一个 config/credentials.py 文件来加载环境变量
# 如果没有，您可以直接在这里使用 os.getenv
# from config.credentials import API_KEY, SECRET_KEY

# 为了让此文件自包含，我们直接在这里加载环境变量
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("ROOSTOO_API_KEY")
SECRET_KEY = os.getenv("ROOSTOO_SECRET_KEY")
# 支持通过环境变量配置API URL，默认使用mock API（用于测试）
# 生产环境请设置 ROOSTOO_API_URL 为真实API地址
BASE_URL = os.getenv("ROOSTOO_API_URL", "https://mock-api.roostoo.com")

class RoostooClient:
    """
    Roostoo API的Python客户端，封装了所有端点的请求和认证逻辑。
    """
    def __init__(self, api_key: str = API_KEY, secret_key: str = SECRET_KEY, base_url: str = None):
        """
        初始化客户端。

        Args:
            api_key (str): 您的Roostoo API Key。
            secret_key (str): 您的Roostoo Secret Key。
            base_url (str, optional): API基础URL。如果为None，使用环境变量ROOSTOO_API_URL或默认值。
        """
        if not api_key or not secret_key:
            raise ValueError("API Key和Secret Key不能为空。请检查您的.env文件或初始化参数。")
        
        # 支持通过参数或环境变量配置base_url
        self.base_url = base_url or BASE_URL
        self.api_key = api_key
        self.secret_key = secret_key
        self.session = requests.Session()
        
        # 打印当前使用的API URL（用于确认）
        if "mock" in self.base_url.lower():
            print(f"[RoostooClient] ⚠️ 使用模拟API: {self.base_url}")
            print(f"[RoostooClient] 如需使用真实API，请在.env中设置 ROOSTOO_API_URL")
        else:
            print(f"[RoostooClient] ✓ 使用真实API: {self.base_url}")

    def _get_timestamp(self) -> str:
        """生成13位毫秒级时间戳字符串。"""
        return str(int(time.time() * 1000))

    def _sign_request(self, payload: Dict[str, Any]) -> Tuple[Dict[str, str], str]:
        """
        为RCL_TopLevelCheck请求生成签名和头部。
        严格遵循README.md中的签名规则。

        Args:
            payload (Dict[str, Any]): 请求的业务参数。

        Returns:
            Tuple[Dict[str, str], str]: 一个元组，包含(请求头, 用于POST data的参数字符串)。
        """
        # 1. 添加时间戳
        payload['timestamp'] = self._get_timestamp()

        # 2. 按照key的字母顺序排序参数
        sorted_payload = sorted(payload.items())

        # 3. 拼接成 "key1=value1&key2=value2" 格式的字符串
        total_params = urlencode(sorted_payload)

        # 4. 使用HMAC-SHA256算法生成签名
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            total_params.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # 5. 构建请求头
        headers = {
            'RST-API-KEY': self.api_key,
            'MSG-SIGNATURE': signature
        }
        
        return headers, total_params

    def _request(self, method: str, path: str, **kwargs):
        """
        通用的请求发送方法，包含统一的错误处理。

        Args:
            method (str): HTTP方法 (GET, POST)。
            path (str): API端点路径。
            **kwargs: 传递给 requests 的其他参数 (headers, params, data)。
        
        Returns:
            Dict: API返回的JSON数据。
        """
        url = f"{self.base_url}{path}"
        try:
            response = self.session.request(method, url, **kwargs, timeout=10)
            response.raise_for_status()  # 如果状态码是4xx或5xx，则抛出异常
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP错误: {e.response.status_code} - {e.response.reason}")
            print(f"URL: {e.response.url}")
            print(f"响应内容: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            print(f"请求发生异常: {e}")
            raise

    # --- Public API Endpoints ---

    def check_server_time(self) -> Dict:
        """[RCL_NoVerification] 检查服务器时间"""
        return self._request('GET', '/v3/serverTime')

    def get_exchange_info(self) -> Dict:
        """[RCL_NoVerification] 获取交易所信息，包括交易对、精度等"""
        return self._request('GET', '/v3/exchangeInfo')

    def get_ticker(self, pair: Optional[str] = None) -> Dict:
        """[RCL_TSCheck] 获取市场Ticker信息"""
        params = {'timestamp': self._get_timestamp()}
        if pair:
            params['pair'] = pair
        return self._request('GET', '/v3/ticker', params=params)

    def get_balance(self) -> Dict:
        """[RCL_TopLevelCheck] 获取账户余额信息"""
        headers, _ = self._sign_request({})
        # 对于GET请求，timestamp需要作为URL参数
        params = {'timestamp': headers.pop('timestamp', self._get_timestamp())} # 从payload中提取timestamp
        return self._request('GET', '/v3/balance', headers=headers, params={'timestamp': self._get_timestamp()})

    def get_pending_count(self) -> Dict:
        """[RCL_TopLevelCheck] 获取挂单数量"""
        headers, _ = self._sign_request({})
        return self._request('GET', '/v3/pending_count', headers=headers, params={'timestamp': self._get_timestamp()})

    def place_order(self, pair: str, side: str, quantity: float, price: Optional[float] = None) -> Dict:
        """[RCL_TopLevelCheck] 下新订单（市价或限价）"""
        payload = {
            'pair': pair,
            'side': side.upper(), # 'BUY' or 'SELL'
            'quantity': str(quantity),
        }
        if price is not None:
            payload['order_type'] = 'LIMIT'
            payload['price'] = str(price)
        else:
            payload['order_type'] = 'MARKET'
        
        headers, data_string = self._sign_request(payload)
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        return self._request('POST', '/v3/place_order', headers=headers, data=data_string)

    def query_order(self, order_id: Optional[str] = None, pair: Optional[str] = None) -> Dict:
        """[RCL_TopLevelCheck] 查询订单"""
        payload = {}
        if order_id:
            payload['order_id'] = order_id
        elif pair:
            payload['pair'] = pair
            
        headers, data_string = self._sign_request(payload)
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        return self._request('POST', '/v3/query_order', headers=headers, data=data_string)

    def cancel_order(self, order_id: Optional[str] = None, pair: Optional[str] = None) -> Dict:
        """[RCL_TopLevelCheck] 取消订单"""
        payload = {}
        if order_id:
            payload['order_id'] = order_id
        elif pair:
            payload['pair'] = pair
            
        headers, data_string = self._sign_request(payload)
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        return self._request('POST', '/v3/cancel_order', headers=headers, data=data_string)