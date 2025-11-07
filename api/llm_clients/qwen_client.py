import os
import requests
from typing import List, Dict, Any, Optional

from .base import LLMClient


class QwenClient(LLMClient):
    """
    Qwen 客户端，支持两种调用方式：
    1) DashScope 官方 SDK（若安装且开启 USE_QWEN_SDK=true）
    2) 兼容 OpenAI 风格的 HTTP REST 接口
    两种方式都会标准化返回 {"content": str, "raw": Any}
    """

    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 default_model: Optional[str] = None,
                 timeout_seconds: int = 30):
        # 允许使用 QWEN_API_KEY 或 DASHSCOPE_API_KEY
        self.api_key = api_key or os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        
        # 处理 base_url：如果用户设置了兼容模式端点，需要确保路径正确
        env_base_url = base_url or os.getenv("QWEN_BASE_URL", "https://api.qwen.ai")
        
        # 如果 base_url 已经包含完整路径（如兼容模式），直接使用
        # 否则使用默认的 Qwen OpenAI 兼容端点
        if env_base_url.endswith("/v1") or env_base_url.endswith("/compatible-mode/v1"):
            # 用户已经指定了包含路径的端点，直接使用
            self.base_url = env_base_url.rstrip("/")
        else:
            # 使用默认的 Qwen OpenAI 兼容端点
            self.base_url = env_base_url.rstrip("/")
        
        self.default_model = default_model or os.getenv("QWEN_MODEL", "qwen-chat")
        self.timeout_seconds = timeout_seconds

        if not self.api_key:
            raise ValueError("QWEN_API_KEY/DASHSCOPE_API_KEY not set")

        # SDK 模式开关
        self.use_sdk = os.getenv("USE_QWEN_SDK", "false").lower() in ("1", "true", "yes")
        self._sdk_ready = False
        if self.use_sdk:
            try:
                # 延迟导入，避免无 SDK 环境下报错
                import dashscope  # type: ignore
                from http import HTTPStatus  # type: ignore
                self._dashscope = dashscope
                self._HTTPStatus = HTTPStatus
                self._sdk_ready = True
            except Exception:
                # 如果 SDK 不可用则回退到 HTTP
                self.use_sdk = False

        # 为 HTTP 模式准备 session
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
        if self.use_sdk and self._sdk_ready:
            return self._chat_via_sdk(messages, model=model, temperature=temperature,
                                      max_tokens=max_tokens, extra_params=extra_params)
        return self._chat_via_http(messages, model=model, temperature=temperature,
                                   max_tokens=max_tokens, extra_params=extra_params)

    def _chat_via_sdk(self, messages: List[Dict[str, str]], *,
                      model: Optional[str],
                      temperature: Optional[float],
                      max_tokens: Optional[int],
                      extra_params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        # DashScope SDK 使用全局环境 DASHSCOPE_API_KEY，无需额外 headers
        call_kwargs: Dict[str, Any] = {
            "model": model or self.default_model,
            "messages": messages,
            "result_format": "message",
        }
        if temperature is not None:
            call_kwargs["temperature"] = temperature
        if max_tokens is not None:
            call_kwargs["max_tokens"] = max_tokens
        if extra_params:
            call_kwargs.update(extra_params)

        resp = self._dashscope.Generation.call(**call_kwargs)
        ok = getattr(resp, "status_code", None) == self._HTTPStatus.OK
        if ok:
            try:
                content = resp.output.choices[0].message.content
            except Exception:
                content = None
            return {"content": content, "raw": resp}
        # 失败时也返回统一结构，方便上层处理
        return {"content": None, "raw": resp}

    def _chat_via_http(self, messages: List[Dict[str, str]], *,
                       model: Optional[str],
                       temperature: Optional[float],
                       max_tokens: Optional[int],
                       extra_params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
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

        # 构建URL：如果base_url已经包含/v1路径，直接拼接/chat/completions
        # 否则需要添加/v1/chat/completions
        if "/v1" in self.base_url or "/compatible-mode" in self.base_url:
            # base_url已经包含路径，直接拼接
            url = f"{self.base_url}/chat/completions"
        else:
            # 使用OpenAI兼容格式
            url = f"{self.base_url}/v1/chat/completions"
        
        # 尝试请求，如果失败则尝试回退到Qwen官方端点
        fallback_base_url = "https://api.qwen.ai"
        fallback_url = f"{fallback_base_url}/v1/chat/completions"
        
        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
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
                    f"   - Check if QWEN_API_KEY or DASHSCOPE_API_KEY is set correctly\n"
                    f"   - Verify the API key is valid and not expired\n"
                    f"   - Make sure there are no extra spaces or quotes in the key\n"
                    f"   Current base_url: {self.base_url}\n"
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
                # 如果是404错误，且当前使用的是DashScope兼容模式端点，尝试回退到Qwen官方端点
                if "dashscope.aliyuncs.com" in self.base_url and url != fallback_url:
                    try:
                        # 尝试使用Qwen官方端点
                        resp = self.session.post(fallback_url, json=payload, timeout=self.timeout_seconds)
                        resp.raise_for_status()
                        data = resp.json()
                        content = None
                        try:
                            content = data["choices"][0]["message"]["content"]
                        except Exception:
                            content = None
                        return {"content": content, "raw": data}
                    except Exception as fallback_error:
                        # 回退也失败，返回原始错误信息
                        error_msg = (
                            f"❌ Endpoint Not Found (404): {url}\n"
                            f"🌐 This means the API URL is INCORRECT or the endpoint doesn't exist.\n"
                            f"   - The endpoint '{url}' was not found\n"
                            f"   - Fallback to {fallback_url} also failed: {fallback_error}\n"
                            f"   - Try setting QWEN_BASE_URL='https://api.qwen.ai' in your environment\n"
                            f"   - Or use DashScope SDK by setting USE_QWEN_SDK=true\n"
                            f"   Current base_url: {self.base_url}\n"
                            f"   Response: {response_text}"
                        )
                else:
                    error_msg = (
                        f"❌ Endpoint Not Found (404): {url}\n"
                        f"🌐 This means the API URL is INCORRECT or the endpoint doesn't exist.\n"
                        f"   - Check if QWEN_BASE_URL is set correctly\n"
                        f"   - Verify the endpoint path is correct\n"
                        f"   - Try using 'https://api.qwen.ai' as QWEN_BASE_URL\n"
                        f"   Current base_url: {self.base_url}\n"
                        f"   Response: {response_text}"
                    )
            elif status_code == 400:
                error_msg = (
                    f"❌ Bad Request (400): {url}\n"
                    f"📝 This means the REQUEST PARAMETERS are INVALID.\n"
                    f"   - Check if the model name '{model or self.default_model}' is correct\n"
                    f"   - Verify message format is valid\n"
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
                    f"   - Consider upgrading your API plan\n"
                    f"   Current base_url: {self.base_url}\n"
                    f"   Response: {response_text}"
                )
            elif status_code >= 500:
                error_msg = (
                    f"❌ Server Error ({status_code}): {url}\n"
                    f"🔧 This is a SERVER-SIDE error, not a configuration issue.\n"
                    f"   - The API service may be temporarily unavailable\n"
                    f"   - Try again later\n"
                    f"   - Check service status page\n"
                    f"   Current base_url: {self.base_url}\n"
                    f"   Response: {response_text}"
                )
            else:
                error_msg = (
                    f"❌ HTTP Error ({status_code}): {url}\n"
                    f"⚠️  Unexpected error occurred.\n"
                    f"   Current base_url: {self.base_url}\n"
                    f"   Response: {response_text}"
                )
            
            raise requests.exceptions.HTTPError(error_msg, response=e.response) from e
        except requests.exceptions.RequestException as e:
            # 处理网络连接错误等其他请求异常
            error_msg = (
                f"❌ Network/Connection Error: {url}\n"
                f"🌐 This means there's a NETWORK or CONNECTION problem.\n"
                f"   - Check your internet connection\n"
                f"   - Verify the base_url is reachable\n"
                f"   - Check firewall/proxy settings\n"
                f"   Current base_url: {self.base_url}\n"
                f"   Error: {str(e)}"
            )
            raise requests.exceptions.RequestException(error_msg) from e


if __name__ == "__main__":
    # 小示例：优先使用 SDK（若已安装并设置 USE_QWEN_SDK=true），否则走 HTTP
    client = QwenClient()
    demo_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "用 Python 写一个冒泡排序函数。"},
    ]
    out = client.chat(demo_messages, max_tokens=200)
    print(out.get("content"))
