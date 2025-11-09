import os
import requests
from typing import List, Dict, Any, Optional

from .base import LLMClient


class MiniMaxClient(LLMClient):
    """
    MiniMax 客户端，支持 MiniMax API 调用
    标准化返回 {"content": str, "raw": Any}
    """

    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 default_model: Optional[str] = None,
                 group_id: Optional[str] = None,
                 timeout_seconds: int = 30):
        # 获取配置参数
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY")
        self.group_id = group_id or os.getenv("MINIMAX_GROUP_ID", "")
        self.base_url = base_url or os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1")
        # 修正模型名称
        self.default_model = default_model or os.getenv("MINIMAX_MODEL", "mini-max-2")
        self.timeout_seconds = timeout_seconds

        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY not set")
        if not self.group_id:
            raise ValueError("MINIMAX_GROUP_ID not set - required for MiniMax models")

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
        return self._chat_via_http(messages, model=model, temperature=temperature,
                                   max_tokens=max_tokens, extra_params=extra_params)

    def _chat_via_http(self, messages: List[Dict[str, str]], *,
                       model: Optional[str],
                       temperature: Optional[float],
                       max_tokens: Optional[int],
                       extra_params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        MiniMax API 调用
        参考文档: https://api.minimax.chat/document/guides/chat
        """
        # MiniMax 原生请求格式
        payload: Dict[str, Any] = {
            "model": model or self.default_model,
            "messages": self._convert_to_minimax_messages(messages),
            "stream": False,
            "bot_setting": [
                {
                    "bot_name": "AI Assistant",
                    "content": "You are a helpful AI assistant."
                }
            ],
            "reply_constraints": {
                "sender_type": "BOT",
                "sender_name": "AI Assistant"
            }
        }

        # 添加可选参数
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["tokens_to_generate"] = max_tokens  # MiniMax 参数名
        if self.group_id:
            payload["group_id"] = self.group_id

        # 合并额外参数
        if extra_params:
            payload.update(extra_params)

        # 正确的端点
        url = f"{self.base_url.rstrip('/')}/text/chatcompletion_v2"

        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
            
            # 解析 MiniMax 响应
            content = self._parse_minimax_response(data)
            return {"content": content, "raw": data}
            
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            response_text = ""
            try:
                response_text = e.response.text[:500]
            except Exception:
                response_text = "N/A"
            
            # 提供详细的错误诊断信息
            if status_code == 401:
                error_msg = (
                    f"❌ MiniMax Authentication Failed (401 Unauthorized): {url}\n"
                    f"🔑 This means your MINIMAX_API_KEY is INVALID or MISSING.\n"
                    f"   - Check if MINIMAX_API_KEY is set correctly\n"
                    f"   - Verify the API key is valid and not expired\n"
                    f"   Current base_url: {self.base_url}\n"
                    f"   Response: {response_text}"
                )
            elif status_code == 403:
                error_msg = (
                    f"❌ MiniMax Access Forbidden (403 Forbidden): {url}\n"
                    f"🔒 This means your API key is valid but lacks PERMISSIONS.\n"
                    f"   - Check if your API key has access to the requested model\n"
                    f"   - Verify your account has sufficient credits/quota\n"
                    f"   - Check if the model name '{model or self.default_model}' is correct\n"
                    f"   Current base_url: {self.base_url}\n"
                    f"   Response: {response_text}"
                )
            elif status_code == 400:
                error_msg = (
                    f"❌ MiniMax Bad Request (400): {url}\n"
                    f"📝 This means the REQUEST PARAMETERS are INVALID.\n"
                    f"   - Check if the model name '{model or self.default_model}' is correct\n"
                    f"   - Verify message format is valid\n"
                    f"   - Check if temperature/tokens_to_generate values are within valid range\n"
                    f"   - Check if group_id is required and set correctly\n"
                    f"   Current base_url: {self.base_url}\n"
                    f"   Response: {response_text}"
                )
            elif status_code == 429:
                error_msg = (
                    f"❌ MiniMax Rate Limit Exceeded (429): {url}\n"
                    f"⏱️  This means you've exceeded the API RATE LIMIT.\n"
                    f"   - Wait a few moments and try again\n"
                    f"   - Check your API quota/usage limits\n"
                    f"   Current base_url: {self.base_url}\n"
                    f"   Response: {response_text}"
                )
            elif status_code >= 500:
                error_msg = (
                    f"❌ MiniMax Server Error ({status_code}): {url}\n"
                    f"🔧 This is a SERVER-SIDE error, not a configuration issue.\n"
                    f"   - The MiniMax API service may be temporarily unavailable\n"
                    f"   - Try again later\n"
                    f"   Current base_url: {self.base_url}\n"
                    f"   Response: {response_text}"
                )
            else:
                error_msg = (
                    f"❌ MiniMax HTTP Error ({status_code}): {url}\n"
                    f"⚠️  Unexpected error occurred.\n"
                    f"   Current base_url: {self.base_url}\n"
                    f"   Response: {response_text}"
                )
            
            raise requests.exceptions.HTTPError(error_msg, response=e.response) from e
        except requests.exceptions.RequestException as e:
            error_msg = (
                f"❌ MiniMax Network/Connection Error: {url}\n"
                f"🌐 This means there's a NETWORK or CONNECTION problem.\n"
                f"   - Check your internet connection\n"
                f"   - Verify the base_url is reachable\n"
                f"   Current base_url: {self.base_url}\n"
                f"   Error: {str(e)}"
            )
            raise requests.exceptions.RequestException(error_msg) from e

    def _convert_to_minimax_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        将标准消息格式转换为 MiniMax 原生格式
        MiniMax 使用 sender_type: "USER" 或 "BOT"
        """
        minimax_messages = []
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            # MiniMax 角色映射
            if role == "system":
                # 系统消息可以放在 bot_setting 或作为用户消息处理
                minimax_messages.append({"sender_type": "USER", "text": content})
            elif role == "user":
                minimax_messages.append({"sender_type": "USER", "text": content})
            elif role == "assistant":
                minimax_messages.append({"sender_type": "BOT", "text": content})
            else:
                # 默认处理为用户消息
                minimax_messages.append({"sender_type": "USER", "text": content})
                
        return minimax_messages

    def _parse_minimax_response(self, data: Dict[str, Any]) -> Optional[str]:
        """
        解析 MiniMax API 响应，提取回复内容
        """
        try:
            # MiniMax 原生响应结构
            if data.get("base_resp", {}).get("status_code") == 0:
                choices = data.get("choices", [])
                if choices:
                    # 获取第一个选择的消息内容
                    message = choices[0].get("text", "")
                    # 清理可能的格式问题
                    if message.startswith('"') and message.endswith('"'):
                        message = message[1:-1]
                    return message
            else:
                # API 返回错误
                error_msg = data.get("base_resp", {}).get("status_msg", "Unknown error")
                print(f"MiniMax API Error: {error_msg}")
                return None
                
        except Exception as e:
            print(f"Error parsing MiniMax response: {e}")
            return None

    def get_models(self) -> List[str]:
        """
        获取可用的 MiniMax 模型列表
        """
        return [
            "mini-max-2",    # 修正模型名称
            "abab6.5-chat",
            "abab5.5-chat", 
            "abab5-chat",
            "abab4-chat"
        ]


if __name__ == "__main__":
    # 测试示例
    client = MiniMaxClient()
    demo_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "用 Python 写一个冒泡排序函数。"},
    ]
    out = client.chat(demo_messages, max_tokens=200)
    print("MiniMax Response:")
    print(out.get("content"))
    print("\nRaw response structure:")
    print(out.get("raw"))
