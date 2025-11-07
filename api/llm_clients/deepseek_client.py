import os
import requests
from typing import List, Dict, Any, Optional

from .base import LLMClient # 从base.py导入LLMClient接口

class DeepSeekClient(LLMClient): # 声明DeepSeekClient继承自LLMClient，承诺遵守其契约
    def __init__(self, # 类的构造函数，当创建DeepSeekClient实例时被调用
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 default_model: Optional[str] = None,
                 timeout_seconds: int = 30):
        
        # --- 配置加载 ---
        # 优先使用直接传入的api_key，如果没有，则尝试从环境变量"DEEPSEEK_API_KEY"中读取。
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        # 同样，为base_url和default_model设置默认值或从环境变量读取。
        # 支持两种格式：https://api.deepseek.com 或 https://api.deepseek.com/v1 (OpenAI compatible)
        env_base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        # 移除末尾的斜杠（如果有），保持base_url格式统一
        self.base_url = env_base_url.rstrip("/")
        self.default_model = default_model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.timeout_seconds = timeout_seconds

        # --- 认证检查 ---
        if not self.api_key: # 如果最终没有获取到API Key，则抛出错误，防止后续调用失败。
            raise ValueError("DEEPSEEK_API_KEY not set")

        # --- 初始化HTTP会话 ---
        # 使用requests.Session()而不是单个的requests.post()，可以复用TCP连接，效率更高。
        self.session = requests.Session()
        # 更新会话的请求头，这样后续所有使用此session的请求都会自动带上这些头信息。
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}", # Bearer Token认证
            "Content-Type": "application/json"
        })

    def chat(self, messages: List[Dict[str, str]], *, # 实现base.py中定义的chat方法
             model: Optional[str] = None,
             temperature: Optional[float] = None,
             max_tokens: Optional[int] = None,
             extra_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        
        # --- 构建请求体 (Payload) ---
        payload: Dict[str, Any] = {
            # 如果调用时传入了model，就用传入的，否则用__init__时设置的默认模型。
            "model": model or self.default_model,
            "messages": messages,
            "stream": False, # 这里硬编码为非流式输出
        }
        # 只有当temperature等参数被实际传入时，才将它们添加到payload中。这可以避免发送如 "temperature": null 的值。
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if extra_params:
            payload.update(extra_params) # 合并额外的自定义参数

        # --- 发送HTTP请求 ---
        # 构建URL：官方支持两种格式
        # - https://api.deepseek.com/chat/completions
        # - https://api.deepseek.com/v1/chat/completions (OpenAI compatible)
        url = f"{self.base_url}/chat/completions"
        
        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout_seconds)
            resp.raise_for_status() # 这是一个非常有用的函数，如果HTTP响应状态码是4xx或5xx（表示错误），它会自动抛出异常。
            data = resp.json() # 将返回的JSON字符串解析为Python字典。

            # --- 格式化返回结果 ---
            # 这是将特定API的返回结果"标准化"为我们接口要求的格式的关键步骤。
            content = None
            try:
                # 尝试从DeepSeek返回的复杂JSON结构中，按路径提取出模型生成的文本内容。
                content = data["choices"][0]["message"]["content"]
            except Exception:
                # 如果提取失败（例如API返回了错误信息，结构不同），保持content为None，避免程序崩溃。
                content = None

            # 按照base.py中定义的契约，返回一个包含标准'content'和原始'raw'数据的字典。
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
                    f"   - Check if DEEPSEEK_API_KEY is set correctly in your environment\n"
                    f"   - Verify the API key is valid and not expired\n"
                    f"   - Make sure there are no extra spaces or quotes in the key\n"
                    f"   - Get your API key from: https://platform.deepseek.com\n"
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
                    f"   - Available models: 'deepseek-chat', 'deepseek-reasoner', 'deepseek-coder'\n"
                    f"   - Note: deepseek-chat and deepseek-reasoner are both DeepSeek-V3.2-Exp\n"
                    f"   Current base_url: {self.base_url}\n"
                    f"   Response: {response_text}"
                )
            elif status_code == 404:
                error_msg = (
                    f"❌ Endpoint Not Found (404): {url}\n"
                    f"🌐 This means the API URL is INCORRECT or the endpoint doesn't exist.\n"
                    f"   - Check if DEEPSEEK_BASE_URL is set correctly\n"
                    f"   - Expected URLs: https://api.deepseek.com/chat/completions or https://api.deepseek.com/v1/chat/completions\n"
                    f"   - Verify the endpoint path is correct\n"
                    f"   Current base_url: {self.base_url}\n"
                    f"   Response: {response_text}"
                )
            elif status_code == 400:
                error_msg = (
                    f"❌ Bad Request (400): {url}\n"
                    f"📝 This means the REQUEST PARAMETERS are INVALID.\n"
                    f"   - Check if the model name '{model or self.default_model}' is correct\n"
                    f"   - Valid models: 'deepseek-chat', 'deepseek-reasoner', 'deepseek-coder'\n"
                    f"   - Note: deepseek-chat (non-reasoning) and deepseek-reasoner (reasoning) are DeepSeek-V3.2-Exp\n"
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
                    f"   - Check your API quota/usage limits at https://platform.deepseek.com\n"
                    f"   - Consider upgrading your API plan if needed\n"
                    f"   Current base_url: {self.base_url}\n"
                    f"   Response: {response_text}"
                )
            elif status_code >= 500:
                error_msg = (
                    f"❌ Server Error ({status_code}): {url}\n"
                    f"🔧 This is a SERVER-SIDE error, not a configuration issue.\n"
                    f"   - The DeepSeek API service may be temporarily unavailable\n"
                    f"   - Try again later\n"
                    f"   - Check service status at https://platform.deepseek.com\n"
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
                f"   - Try accessing https://api.deepseek.com in your browser\n"
                f"   Error: {str(e)}"
            )
            raise requests.exceptions.RequestException(error_msg) from e