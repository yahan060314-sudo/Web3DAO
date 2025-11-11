# roostoo_client.py (完整修复版)
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
        # 支持通过参数或环境变量配置base_url
        self.base_url = base_url or BASE_URL
        
        # 检查是否是Mock API
        is_mock_api = "mock" in self.base_url.lower()
        
        # 检查是否提供了真实的API凭证
        # 排除占位符值（如 "your_roostoo_api_key_here"）
        is_placeholder = (
            (api_key and ("your_" in api_key.lower() or "placeholder" in api_key.lower() or "here" in api_key.lower() or len(api_key) < 10)) or
            (secret_key and ("your_" in secret_key.lower() or "placeholder" in secret_key.lower() or "here" in secret_key.lower() or len(secret_key) < 10))
        )
        
        has_real_credentials = (
            api_key and 
            secret_key and 
            api_key.strip() != "" and 
            secret_key.strip() != "" and
            api_key != "mock_api_key" and 
            secret_key != "mock_secret_key" and
            not is_placeholder  # 排除占位符
        )
        
        if is_mock_api:
            print(f"[RoostooClient] ⚠️ 使用模拟API: {self.base_url}")
            
            if has_real_credentials:
                # 如果提供了真实的API凭证，即使在Mock API模式下也使用真实凭证
                # 这样可以让Mock API的余额接口等需要认证的端点正常工作
                self.api_key = api_key
                self.secret_key = secret_key
                print(f"[RoostooClient] ✓ 使用真实API凭证（Mock API模式下，某些接口需要有效凭证）")
            else:
                # 如果没有提供真实的API凭证，使用测试凭证
                # 这适用于只需要测试公开接口（如服务器时间、交易所信息）的场景
                self.api_key = api_key or "mock_api_key"
                self.secret_key = secret_key or "mock_secret_key"
                
                # 检查是否是占位符
                if is_placeholder:
                    print(f"[RoostooClient] ⚠️ 检测到占位符值，使用测试凭证")
                    print(f"[RoostooClient] 💡 提示: 请在.env文件中填入真实的API凭证（不是占位符）")
                    print(f"[RoostooClient] 💡 当前使用的是占位符，余额接口将无法使用")
                else:
                    print(f"[RoostooClient] ⚠️ 使用测试凭证（Mock API模式下，仅公开接口可用）")
                    print(f"[RoostooClient] 💡 提示: 如需测试余额等需要认证的接口，请在.env中配置真实的API凭证")
            
            print(f"[RoostooClient] 如需使用真实API，请在.env中设置 ROOSTOO_API_URL=https://api.roostoo.com")
        else:
            # 真实API必须提供有效的凭证
            if not api_key or not secret_key:
                raise ValueError("API Key和Secret Key不能为空。请检查您的.env文件或初始化参数。")
            self.api_key = api_key
            self.secret_key = secret_key
            print(f"[RoostooClient] ✓ 使用真实API: {self.base_url}")
        
        self.session = requests.Session()

    def _get_timestamp(self) -> int:
        """生成13位毫秒级时间戳整数。"""
        return int(time.time() * 1000)

    def _generate_signature(self, param_string: str) -> str:
        """
        生成HMAC SHA256签名
        
        Args:
            param_string: 参数字符串
            
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
        构建参数字符串（按字母顺序排序）
        
        Args:
            params: 参数字典
            
        Returns:
            排序后的参数字符串
        """
        sorted_params = sorted(params.items())
        param_string = "&".join(f"{k}={v}" for k, v in sorted_params)
        return param_string

    def _sign_request(self, payload: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, Any], str]:
        """
        为RCL_TopLevelCheck请求生成签名和头部。
        
        Args:
            payload: 请求参数字典
            
        Returns:
            Tuple[请求头, 签名后的参数字典, 参数字符串]
        """
        # 添加时间戳
        payload_with_timestamp = payload.copy()
        payload_with_timestamp['timestamp'] = self._get_timestamp()
        
        # 构建参数字符串
        param_string = self._build_param_string(payload_with_timestamp)
        
        # 生成签名
        signature = self._generate_signature(param_string)

        headers = {
            'RST-API-KEY': self.api_key,
            'MSG-SIGNATURE': signature
        }
        
        return headers, payload_with_timestamp, param_string

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
        
        # 安全打印请求信息
        if 'headers' in kwargs:
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
                response = self.session.request(method, url, **kwargs, timeout=timeout)
                response.raise_for_status()
                print(f"[RoostooClient] ✓ 请求成功: {response.status_code}")
                return response.json()
            except requests.exceptions.HTTPError as e:
                print(f"[RoostooClient] ✗ HTTP错误: {e.response.status_code} - {e.response.reason}")
                print(f"    响应内容: {e.response.text}")
                
                # 针对401错误提供更详细的诊断信息
                if e.response.status_code == 401:
                    error_msg = (
                        f"\n[RoostooClient] 认证失败 (401 Unauthorized)\n"
                        f"可能的原因:\n"
                        f"  1. API Key 或 Secret Key 无效\n"
                        f"  2. 使用了占位符值（如 'your_roostoo_api_key_here'）\n"
                        f"  3. API凭证已过期或 revoked\n"
                        f"  4. Mock API 需要有效的API凭证\n"
                        f"建议:\n"
                        f"  1. 检查 .env 文件中的 ROOSTOO_API_KEY 和 ROOSTOO_SECRET_KEY\n"
                        f"  2. 确保使用的是真实的API凭证（不是占位符）\n"
                        f"  3. 验证API凭证是否有效\n"
                        f"  4. 如果使用Mock API，某些接口可能需要有效的凭证\n"
                        f"  5. 当前使用的API Key: {self.api_key[:15] + '...' if len(self.api_key) > 15 else self.api_key}"
                    )
                    print(error_msg)
                
                # 401, 403, 451等认证错误不重试，直接抛出
                if e.response.status_code in [401, 403, 451]:
                    raise
                
                # 其他HTTP错误可以重试
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    print(f"[RoostooClient] ⚠️ HTTP错误 (尝试 {attempt + 1}/{max_retries})，{wait_time:.1f}秒后重试...")
                    time.sleep(wait_time)
                else:
                    raise
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    print(f"[RoostooClient] ⚠️ 请求异常 (尝试 {attempt + 1}/{max_retries})，{wait_time:.1f}秒后重试...")
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

    def get_trading_rules(self, pair: str = None) -> Dict:
        """
        获取交易规则信息
        """
        exchange_info = self.get_exchange_info()
        trade_pairs = exchange_info.get('TradePairs', {})
        
        if pair:
            return trade_pairs.get(pair, {})
        else:
            return trade_pairs

    def adjust_quantity(self, pair: str, quantity: float) -> float:
        """
        根据交易规则调整数量精度
        
        Args:
            pair: 交易对，如 "BTC/USD"
            quantity: 原始数量
            
        Returns:
            调整后的数量
        """
        try:
            rules = self.get_trading_rules(pair)
            if not rules:
                print(f"[RoostooClient] ⚠️ 未找到交易对 {pair} 的规则，使用默认精度")
                return round(quantity, 6)  # 默认6位小数
            
            amount_precision = rules.get('AmountPrecision', 6)
            
            # 调整精度
            adjusted_quantity = round(quantity, amount_precision)
            
            print(f"[RoostooClient] 数量调整: {quantity} -> {adjusted_quantity} (精度: {amount_precision}位)")
            return adjusted_quantity
            
        except Exception as e:
            print(f"[RoostooClient] ❌ 调整数量精度失败: {e}")
            return round(quantity, 6)  # 失败时使用默认精度

    def get_current_price(self, pair: str) -> float:
        """
        获取当前价格
        """
        try:
            ticker = self.get_ticker(pair)
            price_data = ticker.get('Data', {}).get(pair, {})
            return price_data.get('LastPrice', 0.0)
        except Exception as e:
            print(f"[RoostooClient] ❌ 获取价格失败: {e}")
            return 0.0

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
        """[RCL_TopLevelCheck] 获取账户余额信息"""
        headers, signed_params, _ = self._sign_request({})
        return self._request('GET', '/v3/balance', headers=headers, params=signed_params, timeout=timeout)

    def get_pending_count(self, timeout: Optional[float] = None) -> Dict:
        """[RCL_TopLevelCheck] 获取挂单数量"""
        headers, signed_params, _ = self._sign_request({})
        return self._request('GET', '/v3/pending_count', headers=headers, params=signed_params, timeout=timeout)

    def place_order(self, pair: str, side: str, quantity: float, price: Optional[float] = None) -> Dict:
        """
        [RCL_TopLevelCheck] 下新订单（市价或限价）- 带精度调整
        """
        # 调整数量精度
        adjusted_quantity = self.adjust_quantity(pair, quantity)
        
        # 构建payload
        payload = {
            "pair": pair,
            "side": side.upper(),
            "quantity": str(adjusted_quantity),  # 使用调整后的数量
        }
        
        if price is not None:
            payload['type'] = 'LIMIT'
            payload['price'] = str(price)
        else:
            payload['type'] = 'MARKET'
        
        # 生成签名和请求头
        headers, _, data_string = self._sign_request(payload)
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        print(f"[RoostooClient] 下单请求:")
        print(f"  交易对: {pair}")
        print(f"  方向: {side}")
        print(f"  原始数量: {quantity}")
        print(f"  调整后数量: {adjusted_quantity}")
        print(f"  类型: {payload['type']}")
        if price:
            print(f"  价格: {price}")
        print(f"  请求数据: {data_string}")
        
        return self._request('POST', '/v3/place_order', headers=headers, data=data_string)

    def query_order(self, order_id: Optional[str] = None, pair: Optional[str] = None) -> Dict:
        """[RCL_TopLevelCheck] 查询订单"""
        payload = {}
        if order_id:
            payload['order_id'] = order_id
        elif pair:
            payload['pair'] = pair
            
        headers, _, data_string = self._sign_request(payload)
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        return self._request('POST', '/v3/query_order', headers=headers, data=data_string)

    def cancel_order(self, order_id: Optional[str] = None, pair: Optional[str] = None) -> Dict:
        """[RCL_TopLevelCheck] 取消订单"""
        payload = {}
        if order_id:
            payload['order_id'] = order_id
        elif pair:
            payload['pair'] = pair
            
        headers, _, data_string = self._sign_request(payload)
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        return self._request('POST', '/v3/cancel_order', headers=headers, data=data_string)


# 测试函数
def test_precision_and_order():
    """测试精度调整和下单功能"""
    client = RoostooClient()
    
    print("🔍 测试交易数量精度调整和下单")
    print("=" * 50)
    
    try:
        # 获取交易规则
        rules = client.get_trading_rules("BTC/USD")
        print("📋 BTC/USD 交易规则:")
        print(f"  数量精度: {rules.get('AmountPrecision')} 位小数")
        print(f"  价格精度: {rules.get('PricePrecision')} 位小数") 
        print(f"  最小订单: ${rules.get('MiniOrder', 1.0)}")
        
        # 测试问题数量的调整
        problem_quantity = 0.02844915410707636
        print(f"\n🧪 测试问题数量调整:")
        print(f"  原始数量: {problem_quantity}")
        adjusted = client.adjust_quantity("BTC/USD", problem_quantity)
        print(f"  调整后数量: {adjusted}")
        
        # 测试下单
        print(f"\n🚀 测试修正后的下单:")
        result = client.place_order(
            pair="BTC/USD",
            side="BUY",
            quantity=problem_quantity,  # 原始问题数量
            price=105451.29
        )
        print(f"✅ 下单结果: {result}")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    test_precision_and_order()
