import os
import requests
from typing import List, Dict, Any, Optional
from .base import LLMClient

class MiniMaxClient(LLMClient):
    """
    修正版的 MiniMax 客户端 - 修复消息格式问题
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
        
        # 转换为 MiniMax 格式
        minimax_messages = self._convert_messages(messages)
        
        # 构建请求数据 - 使用正确的格式
        payload = {
            "model": model or self.default_model,
            "messages": minimax_messages,
            "bot_setting": [
                {
                    "bot_name": "Trading Assistant",
                    "content": "你是一个专业的加密货币交易助手，必须用JSON格式输出交易决策。"
                }
            ],
            "reply_constraints": {"sender_type": "BOT", "sender_name": "Trading Assistant"},
            "group_id": self.group_id
        }

        # 可选参数
        if temperature is not None:
            payload["temperature"] = max(0.01, min(1.0, temperature))
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens  # 注意：这里改为 max_tokens
        if extra_params:
            payload.update(extra_params)

        url = f"{self.base_url.rstrip('/')}/text/chatcompletion_v2"

        try:
            print(f"[MiniMax] 发送请求到: {url}")
            print(f"[MiniMax] 消息数量: {len(minimax_messages)}")
            
            resp = self.session.post(url, json=payload, timeout=self.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
            
            print(f"[MiniMax] 原始响应状态: {data.get('base_resp', {})}")
            
            content = self._parse_response(data)
            return {"content": content, "raw": data}
            
        except Exception as e:
            print(f"MiniMax API Error: {e}")
            if 'resp' in locals():
                print(f"响应状态码: {resp.status_code}")
                try:
                    print(f"响应内容: {resp.text}")
                except:
                    pass
            return {"content": None, "raw": None, "error": str(e)}

    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        修正消息格式转换 - 解决 "invalid role" 错误
        """
        minimax_messages = []
        
        for msg in messages:
            role = msg.get("role", "").lower()
            content = msg.get("content", "").strip()
            
            if not content:
                continue
                
            # MiniMax 只接受特定的 sender_type 值
            # 根据官方文档，应该是 "USER" 或 "BOT"
            if role in ["user", "system"]:
                sender_type = "USER"
                sender_name = "User"
            elif role == "assistant":
                sender_type = "BOT" 
                sender_name = "Assistant"
            else:
                # 未知角色默认设为 USER
                sender_type = "USER"
                sender_name = "User"
                
            minimax_messages.append({
                "sender_type": sender_type,
                "sender_name": sender_name,
                "text": content
            })
        
        # 确保至少有一条消息
        if not minimax_messages:
            minimax_messages.append({
                "sender_type": "USER",
                "sender_name": "User", 
                "text": "Hello"
            })
            
        print(f"[MiniMax] 转换后的消息: {minimax_messages}")
        return minimax_messages

    def _parse_response(self, data: Dict[str, Any]) -> Optional[str]:
        """
        修正响应解析逻辑
        """
        try:
            # 检查基础响应状态
            base_resp = data.get("base_resp", {})
            status_code = base_resp.get("status_code")
            
            if status_code != 0:
                error_msg = base_resp.get('status_msg', 'Unknown error')
                print(f"[MiniMax] API 错误 {status_code}: {error_msg}")
                return None
            
            # 解析回复内容 - 根据 MiniMax 官方文档格式
            choices = data.get("choices", [])
            if choices and len(choices) > 0:
                # MiniMax 的回复在 choices[0].text
                reply = choices[0].get("text", "").strip()
                if reply:
                    print(f"[MiniMax] 从 choices 解析到回复: {reply[:100]}...")
                    return reply
            
            # 备用解析方式
            if "reply" in data:
                reply = data.get("reply", "").strip()
                if reply:
                    print(f"[MiniMax] 从 reply 字段解析到: {reply[:100]}...")
                    return reply
                
            print("[MiniMax] 未找到有效回复内容")
            return None
            
        except Exception as e:
            print(f"[MiniMax] 解析响应时出错: {e}")
            return None
