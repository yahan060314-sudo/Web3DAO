import os
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from .base import LLMClient

load_dotenv()

class MiniMaxOptimized(LLMClient):
    """
    MiniMax 优化版客户端 - 处理消息限制
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
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

    def chat(self, messages: List[Dict[str, str]], *, 
             model: Optional[str] = None,
             temperature: Optional[float] = None,
             max_tokens: Optional[int] = None,
             extra_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        
        # 优化消息格式 - 合并多个system消息
        optimized_messages = self._optimize_messages(messages)
        
        payload = {
            "model": model or self.default_model,
            "messages": optimized_messages,
            "group_id": self.group_id
        }

        if temperature is not None:
            payload["temperature"] = max(0.01, min(1.0, temperature))
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        url = f"{self.base_url.rstrip('/')}/text/chatcompletion_v2"

        try:
            print(f"[MiniMax] 发送 {len(optimized_messages)} 条优化后的消息")
            
            resp = self.session.post(url, json=payload, timeout=self.timeout_seconds)
            print(f"[MiniMax] 响应状态码: {resp.status_code}")
            
            resp.raise_for_status()
            data = resp.json()
            
            content = self._parse_response(data)
            return {"content": content, "raw": data}
            
        except Exception as e:
            print(f"MiniMax API Error: {e}")
            if 'resp' in locals():
                try:
                    print(f"错误详情: {resp.json()}")
                except:
                    print(f"响应文本: {resp.text}")
            return {"content": None, "raw": None, "error": str(e)}

    def _optimize_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        优化消息格式 - 合并多个system消息，限制消息数量
        """
        if len(messages) <= 2:
            return messages  # 如果消息很少，直接返回
            
        # 合并所有system消息
        system_messages = []
        user_messages = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "").strip()
            
            if not content:
                continue
                
            if role == "system":
                system_messages.append(content)
            else:
                user_messages.append({"role": role, "content": content})
        
        # 构建优化后的消息列表
        optimized = []
        
        # 合并所有system消息为一个
        if system_messages:
            combined_system = "\\n\\n".join(system_messages)
            optimized.append({"role": "system", "content": combined_system})
        
        # 只保留最后一个user消息（避免重复）
        if user_messages:
            optimized.append(user_messages[-1])
        
        print(f"[MiniMax] 消息优化: {len(messages)} -> {len(optimized)} 条")
        return optimized

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
