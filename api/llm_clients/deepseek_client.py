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
        self.base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
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
        url = f"{self.base_url}/chat/completions" # 拼接完整的API Endpoint
        resp = self.session.post(url, json=payload, timeout=self.timeout_seconds)
        resp.raise_for_status() # 这是一个非常有用的函数，如果HTTP响应状态码是4xx或5xx（表示错误），它会自动抛出异常。
        data = resp.json() # 将返回的JSON字符串解析为Python字典。

        # --- 格式化返回结果 ---
        # 这是将特定API的返回结果“标准化”为我们接口要求的格式的关键步骤。
        content = None
        try:
            # 尝试从DeepSeek返回的复杂JSON结构中，按路径提取出模型生成的文本内容。
            content = data["choices"][0]["message"]["content"]
        except Exception:
            # 如果提取失败（例如API返回了错误信息，结构不同），保持content为None，避免程序崩溃。
            content = None

        # 按照base.py中定义的契约，返回一个包含标准'content'和原始'raw'数据的字典。
        return {"content": content, "raw": data}