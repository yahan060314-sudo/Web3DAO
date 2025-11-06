import os
from typing import Optional

from .base import LLMClient # 导入接口
from .deepseek_client import DeepSeekClient # 导入具体实现A
from .qwen_client import QwenClient # 导入具体实现B

def get_llm_client(provider: Optional[str] = None) -> LLMClient:
    """
    根据环境变量 LLM_PROVIDER 或传入的 provider 参数，
    选择并初始化一个具体的LLM客户端。
    支持的提供商: "deepseek", "qwen".
    """
    # 决定使用哪个provider。优先使用函数参数，其次是环境变量，最后默认"deepseek"。
    # .lower()确保了配置不区分大小写（如"DeepSeek"也能正常工作）。
    chosen = (provider or os.getenv("LLM_PROVIDER", "deepseek")).lower()

    # --- 选择逻辑 ---
    if chosen == "deepseek":
        return DeepSeekClient() # 如果是deepseek，就创建并返回一个DeepSeekClient实例。
    if chosen == "qwen":
        return QwenClient() # 如果是qwen，就创建并返回一个QwenClient实例。

    # 如果配置了一个不支持的provider，则抛出错误。
    raise ValueError(f"Unsupported LLM_PROVIDER: {chosen}")