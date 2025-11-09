import os
import requests
from typing import List, Dict, Any, Optional

from .base import LLMClient


class MiniMaxClient(LLMClient):
    """
    MiniMax 客户端实现
    需要将标准 OpenAI 格式转换为 MiniMax 原生格式
    """

    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 default_model: Optional[str] = None,
                 group_id: Optional[str] = None,
                 timeout_seconds: int = 30):
        
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY")
        self.group_id = group_id or os.getenv("MINIMAX_GROUP_ID", "")
        self.base_url = base_url or os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1")
        self.default_model = default_model or os.getenv("MINIMAX_MODEL", "abab6.5-chat")  # 先用稳定模型
        self.timeout_seconds = timeout_seconds

        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY not set")

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
        实现基类接口，将标准消息格式转换为 MiniMax 格式
        """
        # 转换为 MiniMax 原生格式
        minimax_messages = self._convert_to_minimax_format(messages)
        
        payload = {
            "model": model or self.default_model,
            "messages": minimax_messages,
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

        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["tokens_to_generate"] = max_tokens
        if self.group_id:
            payload["group_id"] = self.group_id
        if extra_params:
            payload.update(extra_params)

        url = f"{self.base_url.rstrip('/')}/text/chatcompletion_v2"

        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
            
            content = self._parse_response(data)
            return {"content": content, "raw": data}
            
        except requests.exceptions.HTTPError as e:
            print(f"MiniMax API HTTP Error: {e}")
            return {"content": None, "raw": None, "error": str(e)}
        except Exception as e:
            print(f"MiniMax API Error: {e}")
            return {"content": None, "raw": None, "error": str(e)}

    def _convert_to_minimax_format(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        将标准 OpenAI 格式转换为 MiniMax 原生格式
        """
        minimax_messages = []
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "system":
                # 系统消息可以放在 bot_setting 中，这里作为用户消息处理
                minimax_messages.append({
                    "sender_type": "USER",
                    "text": f"System: {content}"
                })
            elif role == "user":
                minimax_messages.append({
                    "sender_type": "USER", 
                    "text": content
                })
            elif role == "assistant":
                minimax_messages.append({
                    "sender_type": "BOT",
                    "text": content
                })
            else:
                # 未知角色默认作为用户消息
                minimax_messages.append({
                    "sender_type": "USER",
                    "text": content
                })
                
        return minimax_messages

    def _parse_response(self, data: Dict[str, Any]) -> Optional[str]:
        """
        解析 MiniMax API 响应
        """
        try:
            if data.get("base_resp", {}).get("status_code") == 0:
                choices = data.get("choices", [])
                if choices:
                    message = choices[0].get("text", "")
                    # 清理可能的引号
                    if message.startswith('"') and message.endswith('"'):
                        message = message[1:-1]
                    return message
            else:
                error_msg = data.get("base_resp", {}).get("status_msg", "Unknown error")
                print(f"MiniMax API Error: {error_msg}")
                return None
        except Exception as e:
            print(f"Error parsing MiniMax response: {e}")
            return None
