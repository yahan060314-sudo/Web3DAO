import os
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from .base import LLMClient

load_dotenv()

class MiniMaxClient(LLMClient):  # 关键：类名必须是 MiniMaxClient
    """
    修正版的 MiniMax 客户端 - 使用已验证的正确格式
    """

    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 default_model: Optional[str] = None,
                 group_id: Optional[str] = None,
                 timeout_seconds: int = 30):
        
        load_dotenv(override=True)
        
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY")
        self.group_id = group_id or os.getenv("MINIMAX_GROUP_ID", "")
        self.base_url = base_url or os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1")
        self.default_model = default_model or os.getenv("MINIMAX_MODEL", "abab6.5-chat")
        self.timeout_seconds = timeout_seconds

        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY not set")
        if not self.group_id:
            raise ValueError("MINIMAX_GROUP_ID not set")

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
        
        # 使用已验证的正确格式
        payload = {
            "model": model or self.default_model,
            "messages": self._format_messages(messages),
            "group_id": self.group_id
        }

        # 可选参数
        if temperature is not None:
            payload["temperature"] = max(0.01, min(1.0, temperature))
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        url = f"{self.base_url.rstrip('/')}/text/chatcompletion_v2"

        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
            
            content = self._parse_response(data)
            return {"content": content, "raw": data}
            
        except Exception as e:
            print(f"MiniMax API Error: {e}")
            return {"content": None, "raw": None, "error": str(e)}

    def _format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        使用正确的消息格式：role 和 content
        """
        formatted_messages = []
        
        for msg in messages:
            role = msg.get("role", "user").lower()
            content = msg.get("content", "").strip()
            
            if not content:
                continue
                
            formatted_msg = {
                "role": role,
                "content": content
            }
            formatted_messages.append(formatted_msg)
        
        return formatted_messages

    def _parse_response(self, data: Dict[str, Any]) -> Optional[str]:
        """
        解析响应
        """
        try:
            base_resp = data.get("base_resp", {})
            status_code = base_resp.get("status_code")
            
            if status_code != 0:
                return None
            
            choices = data.get("choices", [])
            if choices:
                choice = choices[0]
                message = choice.get("message", {})
                return message.get("content", "").strip()
            
            return None
            
        except Exception:
            return None
            
