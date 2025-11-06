from typing import List, Dict, Any, Optional


class LLMClient:
    """
    Provider-agnostic interface for chat-style LLMs.
    Implementations should accept OpenAI-like messages:
    [{"role": "system|user|assistant", "content": str}]
    and return a dict with at minimum: {"content": str, "raw": Any}.
    """
    """
    这是一个为聊天式大语言模型设计的、与具体提供商无关的接口。
    实现这个接口的类，应该接受类似OpenAI的messages格式:
    [{"role": "system|user|assistant", "content": str}]
    并且返回一个至少包含以下内容的字典: {"content": str, "raw": Any}。
    """

    def chat(self, messages: List[Dict[str, str]], *, 
             model: Optional[str] = None,
             temperature: Optional[float] = None,
             max_tokens: Optional[int] = None,
             extra_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # 定义一个名为 chat 的方法，这是所有子类都必须实现的核心方法。
        # messages: 必需参数，是对话历史列表。
        # *: 星号表示后面的参数必须以关键字形式传递（如 temperature=0.7），增加了代码清晰度。
        # model, temperature, max_tokens: 都是可选的、用于控制模型行为的常见参数。
        # extra_params: 一个字典，用于传递特定模型才有的非通用参数，提供了很好的扩展性。
        # -> Dict[str, Any]: 类型提示，表明此方法返回一个字典。

        raise NotImplementedError
        # 这行代码是关键。它表明 LLMClient 本身不能被直接使用，
        # 任何继承它的子类（如DeepSeekClient）都必须自己重写（implement）这个 chat 方法。
        # 如果子类没有实现它，调用时就会抛出这个错误。


