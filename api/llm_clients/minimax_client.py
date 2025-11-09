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
        self.default_model = default_model or os.getenv("MINIMAX_MODEL", "mini-max-m2")  # 修改默认模型
        self.timeout_seconds = timeout_seconds

        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY not set")

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
        MiniMax-M2 API 调用
        参考文档: https://api.minimax.chat/document/guides/chat-gpt
        """
        # MiniMax-M2 使用 OpenAI 兼容的请求体结构
        payload: Dict[str, Any] = {
            "model": model or self.default_model,
            "messages": self._convert_to_openai_messages(messages),
            "stream": False,
            "top_p": 0.9,
            "with_plugins": False
        }

        # 添加可选参数
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens  # 参数名改为max_tokens

        # 合并额外参数
        if extra_params:
            payload.update(extra_params)

        # 构建URL - MiniMax-M2 使用不同的端点
        url = f"{self.base_url.rstrip('/')}/chat/completions"

        try:
            resp = self.session.post(url, json=payload, timeout=self.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
            
            # 解析 MiniMax-M2 响应
            content = self._parse_minimax_m2_response(data)
            return {"content": content, "raw": data}
            
        except requests.exceptions.HTTPError as e:
            # 错误处理逻辑保持不变...
            # [这里保持原有的错误处理代码]
            pass

    def _convert_to_openai_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        将标准消息格式转换为 OpenAI 兼容格式（MiniMax-M2使用）
        """
        openai_messages = []
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            # MiniMax-M2 使用标准的 OpenAI 角色
            if role in ["system", "user", "assistant"]:
                openai_messages.append({"role": role, "content": content})
            else:
                # 默认处理为用户消息
                openai_messages.append({"role": "user", "content": content})
                
        return openai_messages

    def _parse_minimax_m2_response(self, data: Dict[str, Any]) -> Optional[str]:
        """
        解析 MiniMax-M2 API 响应，提取回复内容
        MiniMax-M2 使用 OpenAI 兼容的响应格式
        """
        try:
            # MiniMax-M2 使用 OpenAI 兼容的响应结构
            choices = data.get("choices", [])
            if choices:
                # 获取第一个选择的消息内容
                message = choices[0].get("message", {})
                content = message.get("content", "")
                return content.strip()
            
            # 检查错误
            if data.get("error"):
                error_msg = data["error"].get("message", "Unknown error")
                print(f"MiniMax-M2 API Error: {error_msg}")
                return None
                
            return None
            
        except Exception as e:
            print(f"Error parsing MiniMax-M2 response: {e}")
            return None

    def get_models(self) -> List[str]:
        """
        获取可用的 MiniMax 模型列表
        """
        return [
            "mini-max-m2",  # 新增 MiniMax-M2
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
    print("MiniMax-M2 Response:")
    print(out.get("content"))
    print("\nRaw response structure:")
    print(out.get("raw"))
