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
    def __init__(self, api_key: str = None, secret_key: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv("ROOSTOO_API_KEY")
        self.secret_key = secret_key or os.getenv("ROOSTOO_SECRET_KEY")
        self.base_url = base_url or os.getenv("ROOSTOO_API_URL", "https://mock-api.roostoo.com")
        self.session = requests.Session()
        
        print(f"[RoostooClient] ✓ 使用API: {self.base_url}")

    def _get_timestamp(self) -> int:
        """生成13位毫秒级时间戳整数（与官方示例保持一致）。"""
        return int(time.time() * 1000)

    def generate_signature(self, params: Dict[str, Any]) -> str:
        """
        生成HMAC SHA256签名。
        严格遵循官方python_demo.py中的generate_signature函数实现。
        
        Args:
            params (Dict[str, Any]): 请求参数字典
            
        Returns:
            str: 签名字符串
        """
        # 按照key的字母顺序排序参数（与官方示例完全一致）
        # 官方示例: query_string = '&'.join(["{}={}".format(k, params[k]) for k in sorted(params.keys())])
        query_string = '&'.join(["{}={}".format(k, params[k]) for k in sorted(params.keys())])
        
        # 使用HMAC-SHA256算法生成签名（与官方示例完全一致）
        us = self.secret_key.encode('utf-8')
        m = hmac.new(us, query_string.encode('utf-8'), hashlib.sha256)
        return m.hexdigest()

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
    
    def check_server_time(self) -> Dict:
        """[RCL_NoVerification] 检查服务器时间"""
        url = f"{self.base_url}/v3/serverTime"
        response = self.session.get(url, timeout=10)
        return response.json()

    def get_exchange_info(self) -> Dict:
        """[RCL_NoVerification] 获取交易所信息"""
        url = f"{self.base_url}/v3/exchangeInfo"
        response = self.session.get(url, timeout=10)
        return response.json()

    def get_ticker(self, pair: str = None) -> Dict:
        """[RCL_TSCheck] 获取市场行情"""
        timestamp = self._get_timestamp()
        params = {'timestamp': timestamp}
        if pair:
            params['pair'] = pair
            
        url = f"{self.base_url}/v3/ticker"
        response = self.session.get(url, params=params, timeout=10)
        return response.json()

    def get_balance(self, timeout: Optional[float] = None) -> Dict:
        """
        [RCL_TopLevelCheck] 获取账户余额信息
        严格按照官方python_demo.py中的get_balance()函数实现。
        """
        # 创建payload字典，包含timestamp（与官方示例完全一致）
        payload = {
            "timestamp": int(time.time() * 1000),
        }
        
        # 生成签名（与官方示例完全一致）
        signature = self.generate_signature(payload)
        
        # 构建请求头（与官方示例完全一致）
        headers = {
            "RST-API-KEY": self.api_key,
            "MSG-SIGNATURE": signature
        }
        
        # 使用params参数，让requests库自动处理查询字符串（与官方示例完全一致）
        return self._request('GET', '/v3/balance', headers=headers, params=payload, timeout=timeout)

    def get_pending_count(self, timeout: Optional[float] = None) -> Dict:
        """
        [RCL_TopLevelCheck] 获取挂单数量
        严格按照官方python_demo.py中的pending_count()函数实现。
        """
        # 创建payload字典，包含timestamp（与官方示例完全一致）
        payload = {
            "timestamp": int(time.time() * 1000),
        }
        
        # 生成签名（与官方示例完全一致）
        signature = self.generate_signature(payload)
        
        # 构建请求头（与官方示例完全一致）
        headers = {
            "RST-API-KEY": self.api_key,
            "MSG-SIGNATURE": signature
        }
        
        # 使用params参数，让requests库自动处理查询字符串（与官方示例完全一致）
        return self._request('GET', '/v3/pending_count', headers=headers, params=payload, timeout=timeout)

    def place_order(self, pair: str, side: str, quantity: float, price: Optional[float] = None) -> Dict:
        """
        [RCL_TopLevelCheck] 下新订单（市价或限价）
        严格按照官方python_demo.py中的place_order()函数实现。
        """
        # 创建payload字典（与官方示例完全一致）
        payload = {
            "timestamp": int(time.time() * 1000),
            "pair": pair,
            "side": side.upper(),
            "quantity": quantity,
        }
        
        # 根据是否有价格设置订单类型（与官方示例完全一致）
        if not price:
            payload['type'] = "MARKET"
        else:
            payload['type'] = "LIMIT"
            payload['price'] = price
        
        # 生成签名（与官方示例完全一致）
        signature = self.generate_signature(payload)
        
        # 构建请求头（与官方示例完全一致）
        headers = {
            "RST-API-KEY": self.api_key,
            "MSG-SIGNATURE": signature
        }
        
        # 使用data参数传递payload字典，requests会自动转换为form-urlencoded格式（与官方示例完全一致）
        return self._request('POST', '/v3/place_order', headers=headers, data=payload)

    def query_order(self, order_id: Optional[str] = None, pair: Optional[str] = None) -> Dict:
        """
        [RCL_TopLevelCheck] 查询订单
        严格按照官方python_demo.py中的query_order()函数实现。
        """
        # 创建payload字典（与官方示例完全一致）
        payload = {
            "timestamp": int(time.time() * 1000),
        }
        if order_id:
            payload['order_id'] = order_id
        elif pair:
            payload['pair'] = pair
        
        # 生成签名（与官方示例完全一致）
        signature = self.generate_signature(payload)
        
        # 构建请求头（与官方示例完全一致）
        headers = {
            "RST-API-KEY": self.api_key,
            "MSG-SIGNATURE": signature
        }
        
        # 使用data参数传递payload字典，requests会自动转换为form-urlencoded格式（与官方示例完全一致）
        return self._request('POST', '/v3/query_order', headers=headers, data=payload)

    def cancel_order(self, order_id: Optional[str] = None, pair: Optional[str] = None) -> Dict:
        """
        [RCL_TopLevelCheck] 取消订单
        严格按照官方python_demo.py中的cancel_order()函数实现。
        """
        # 创建payload字典（与官方示例完全一致）
        payload = {
            "timestamp": int(time.time() * 1000),
        }
        if order_id:
            payload['order_id'] = order_id
        elif pair:
            payload['pair'] = pair
        
        # 生成签名（与官方示例完全一致）
        signature = self.generate_signature(payload)
        
        # 构建请求头（与官方示例完全一致）
        headers = {
            "RST-API-KEY": self.api_key,
            "MSG-SIGNATURE": signature
        }
        
        # 使用data参数传递payload字典，requests会自动转换为form-urlencoded格式（与官方示例完全一致）
        return self._request('POST', '/v3/cancel_order', headers=headers, data=payload)
