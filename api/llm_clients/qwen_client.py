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
        self.base_url = base_url or os.getenv("QWEN_BASE_URL", "https://api.qwen.ai")
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

        url = f"{self.base_url}/chat/completions"
        resp = self.session.post(url, json=payload, timeout=self.timeout_seconds)
        resp.raise_for_status()
        data = resp.json()
        content = None
        try:
            content = data["choices"][0]["message"]["content"]
        except Exception:
            content = None
        return {"content": content, "raw": data}


if __name__ == "__main__":
    # 小示例：优先使用 SDK（若已安装并设置 USE_QWEN_SDK=true），否则走 HTTP
    client = QwenClient()
    demo_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "用 Python 写一个冒泡排序函数。"},
    ]
    out = client.chat(demo_messages, max_tokens=200)
    print(out.get("content"))
