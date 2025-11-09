import os
import requests
from typing import List, Dict, Any, Optional

from .base import LLMClient


class MinimaxClient(LLMClient):
    """
    Minimax AI 客户端，支持 OpenAI 兼容的 API 接口。
    实现标准的 chat 方法，返回格式化的响应。
    """
    
    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 default_model: Optional[str] = None,
                 timeout_seconds: int = 30):
        """
        初始化 Minimax 客户端
        
        Args:
            api_key: API密钥，如果不提供则从环境变量 MINIMAX_API_KEY 读取
            base_url: API基础URL，如果不提供则从环境变量 MINIMAX_BASE_URL 读取，默认使用 https://api.minimax.chat
            default_model: 默认模型名称，如果不提供则从环境变量 MINIMAX_MODEL 读取，默认使用 abab5.5-chat
            timeout_seconds: 请求超时时间（秒）
        """
        # --- 配置加载 ---
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY")
        env_base_url = base_url or os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat")
        self.base_url = env_base_url.rstrip("/")
        self.default_model = default_model or os.getenv("MINIMAX_MODEL", "abab5.5-chat")
        self.timeout_seconds = timeout_seconds

        # --- 认证检查 ---
        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY not set")

        # --- 初始化HTTP会话 ---
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })

    def chat(self, messages: List[Dict[str, str]], *,
             model: Optional[str] = None,
             temperature: Optional[float] = None,
             max_tokens: Optional[int] = None,
             extra_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发送聊天请求到 Minimax API
        
        Args:
            messages: 对话消息列表，格式为 [{"role": "system|user|assistant", "content": str}]
            model: 模型名称，如果不提供则使用默认模型
            temperature: 温度参数，控制输出的随机性
            max_tokens: 最大生成token数
            extra_params: 额外的自定义参数
            
        Returns:
            包含 "content" 和 "raw" 的字典
        """
        # --- 构建请求体 (Payload) ---
        payload: Dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "stream": False,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if extra_params:
            payload.update(extra_params)

        # --- 发送HTTP请求 ---
        # Minimax API 通常使用 OpenAI 兼容的端点格式
        url = f"{self.base_url}/v1/chat/completions"
        
        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()

            # --- 格式化返回结果 ---
            content = None
            try:
                content = data["choices"][0]["message"]["content"]
            except Exception:
                content = None

            return {"content": content, "raw": data}
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            response_text = ""
            try:
                response_text = e.response.text[:500]  # 限制长度
            except Exception:
                response_text = "N/A"
            
            # 根据不同的HTTP状态码提供具体的诊断信息
            if status_code == 401:
                error_msg = (
                    f"❌ Authentication Failed (401 Unauthorized): {url}\n"
                    f"🔑 This means your API key is INVALID or MISSING.\n"
                    f"   - Check if MINIMAX_API_KEY is set correctly in your environment\n"
                    f"   - Verify the API key is valid and not expired\n"
                    f"   - Make sure there are no extra spaces or quotes in the key\n"
                    f"   Current base_url: {self.base_url}\n"
                    f"   Model: {model or self.default_model}\n"
                    f"   Response: {response_text}"
                )
            elif status_code == 403:
                error_msg = (
                    f"❌ Access Forbidden (403 Forbidden): {url}\n"
                    f"🔒 This means your API key is valid but lacks PERMISSIONS.\n"
                    f"   - Check if your API key has access to the requested model\n"
                    f"   - Verify your account has sufficient credits/quota\n"
                    f"   - Check if the model name '{model or self.default_model}' is correct\n"
                    f"   Current base_url: {self.base_url}\n"
                    f"   Response: {response_text}"
                )
            elif status_code == 404:
                error_msg = (
                    f"❌ Endpoint Not Found (404): {url}\n"
                    f"🌐 This means the API URL is INCORRECT or the endpoint doesn't exist.\n"
                    f"   - Check if MINIMAX_BASE_URL is set correctly\n"
                    f"   - Expected URL format: https://api.minimax.chat/v1/chat/completions\n"
                    f"   - Verify the endpoint path is correct\n"
                    f"   Current base_url: {self.base_url}\n"
                    f"   Response: {response_text}"
                )
            elif status_code == 400:
                error_msg = (
                    f"❌ Bad Request (400): {url}\n"
                    f"📝 This means the REQUEST PARAMETERS are INVALID.\n"
                    f"   - Check if the model name '{model or self.default_model}' is correct\n"
                    f"   - Verify message format is valid (must be list of dict with 'role' and 'content')\n"
                    f"   - Check if temperature/max_tokens values are within valid range\n"
                    f"   Current base_url: {self.base_url}\n"
                    f"   Response: {response_text}"
                )
            elif status_code == 429:
                error_msg = (
                    f"❌ Rate Limit Exceeded (429): {url}\n"
                    f"⏱️  This means you've exceeded the API RATE LIMIT.\n"
                    f"   - Wait a few moments and try again\n"
                    f"   - Check your API quota/usage limits\n"
                    f"   - Consider upgrading your API plan if needed\n"
                    f"   Current base_url: {self.base_url}\n"
                    f"   Response: {response_text}"
                )
            elif status_code >= 500:
                error_msg = (
                    f"❌ Server Error ({status_code}): {url}\n"
                    f"🔧 This is a SERVER-SIDE error, not a configuration issue.\n"
                    f"   - The Minimax API service may be temporarily unavailable\n"
                    f"   - Try again later\n"
                    f"   Current base_url: {self.base_url}\n"
                    f"   Response: {response_text}"
                )
            else:
                error_msg = (
                    f"❌ HTTP Error ({status_code}): {url}\n"
                    f"⚠️  Unexpected error occurred.\n"
                    f"   Current base_url: {self.base_url}\n"
                    f"   Model: {model or self.default_model}\n"
                    f"   Response: {response_text}"
                )
            
            raise requests.exceptions.HTTPError(error_msg, response=e.response) from e
        except requests.exceptions.RequestException as e:
            # 处理网络连接错误等其他请求异常
            error_msg = (
                f"❌ Network/Connection Error: {url}\n"
                f"🌐 This means there's a NETWORK or CONNECTION problem.\n"
                f"   - Check your internet connection\n"
                f"   - Verify the base_url is reachable: {self.base_url}\n"
                f"   - Check firewall/proxy settings\n"
                f"   - Try accessing {self.base_url} in your browser\n"
                f"   Error: {str(e)}"
            )
            raise requests.exceptions.RequestException(error_msg) from e


if __name__ == "__main__":
    # 示例用法
    client = MinimaxClient()
    demo_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "你好，请介绍一下你自己。"},
    ]
    out = client.chat(demo_messages, max_tokens=200)
    print(out.get("content"))

