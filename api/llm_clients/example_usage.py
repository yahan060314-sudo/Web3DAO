from typing import List, Dict
from .factory import get_llm_client # 只从factory导入工厂函数

def run_demo():
    # 1. 获取客户端。这里完全不知道也不关心具体是哪个客户端。
    client = get_llm_client() 
    
    # 2. 准备符合OpenAI/LLMClient接口格式的输入。
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": "You are a helpful trading assistant."},
        {"role": "user", "content": "Give a one-sentence outlook on BTC in neutral tone."},
    ]
    
    # 3. 调用统一的chat方法。
    result = client.chat(messages, temperature=0.3, max_tokens=128)
    
    # 4. 打印标准化的输出结果。
    print(result["content"])

if __name__ == "__main__": # 使得这个脚本可以通过 `python -m api.llm_clients.example_usage` 直接运行。
    run_demo()