# Web3DAO

LLM provider-agnostic client layer for DeepSeek/Qwen integration, aligned with Roostoo trading bot.

## Quick Start

### Getting DeepSeek API Key

1. **Visit DeepSeek Platform**: Go to https://platform.deepseek.com
2. **Register/Login**: Create an account or login if you already have one
3. **Get API Key**: 
   - Navigate to "API Keys" or "密钥管理" section
   - Click "Create new API Key" or "生成API密钥"
   - **⚠️ IMPORTANT**: Copy and save your API key immediately (it's usually shown only once)
   - The key typically starts with `sk-`

### Configuration

1) Create a `.env` file at project root:

```
# Select provider: deepseek | qwen | minimax
LLM_PROVIDER=deepseek

# DeepSeek Configuration
DEEPSEEK_API_KEY=sk-your-actual-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com  # Also supports: https://api.deepseek.com/v1 (OpenAI compatible)
DEEPSEEK_MODEL=deepseek-chat  # Options: deepseek-chat (recommended), deepseek-reasoner, or deepseek-coder

# Qwen (AKA DashScope)
QWEN_API_KEY=your_qwen_api_key
QWEN_BASE_URL=https://api.qwen.ai
QWEN_MODEL=qwen-chat

# Minimax Configuration
MINIMAX_API_KEY=your_minimax_api_key
MINIMAX_BASE_URL=https://api.minimax.chat
MINIMAX_MODEL=abab5.5-chat

# Roostoo credentials (already used by api/roostoo_client.py)
ROOSTOO_API_KEY=your_roostoo_api_key
ROOSTOO_SECRET_KEY=your_roostoo_secret
```

**Model Selection for DeepSeek:**
- **`deepseek-chat`** (recommended): DeepSeek-V3.2-Exp in non-reasoning mode. Best for general conversation, reasoning, code generation, and market analysis
- **`deepseek-reasoner`**: DeepSeek-V3.2-Exp in reasoning mode. Use when you need step-by-step thinking process
- **`deepseek-coder`**: Optimized specifically for code generation and completion

**Note**: Both `deepseek-chat` and `deepseek-reasoner` are based on DeepSeek-V3.2-Exp. The difference is that `deepseek-reasoner` shows its reasoning process.

2) Try the LLM demo (it auto-picks provider via `LLM_PROVIDER`):

```
python -m api.llm_clients.example_usage
```

3) Switch providers by changing only `LLM_PROVIDER` and the corresponding API key. Code remains unchanged.

### Multi-AI Integration (综合多个 AI 结果)

如果你想要同时调用多个 AI 提供商并综合输出结果，可以使用 `MultiLLMClient`:

```python
from api.llm_clients import MultiLLMClient

# 创建多 AI 客户端（使用所有可用的提供商）
client = MultiLLMClient()

# 或者指定特定的提供商
client = MultiLLMClient(providers=["deepseek", "qwen", "minimax"])

# 准备消息
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "分析一下 BTC 市场的趋势"}
]

# 并行调用所有 AI
response = client.chat_parallel(messages, temperature=0.7, max_tokens=200)

# 格式化输出结果
print(client.format_results(response, format_type="detailed"))    # 详细输出
print(client.format_results(response, format_type="consolidated")) # 综合输出
print(client.format_results(response, format_type="table"))        # 表格输出
print(client.format_results(response, format_type="summary"))      # 摘要输出

# 获取共识结果
consensus = client.get_consensus(response)
print(f"共识结果数: {consensus['consensus_count']}")
```

运行多 AI 示例：

```
python -m api.llm_clients.multi_llm_example
```

## Structure

- `api/roostoo_client.py`: Roostoo REST client
- `api/data_fetcher.py`: polling example against Roostoo
- `api/llm_clients/`: provider-agnostic LLM interface
  - `base.py`: `LLMClient` interface
  - `deepseek_client.py`, `qwen_client.py`, `minimax_client.py`: concrete implementations
  - `factory.py`: selects provider via `LLM_PROVIDER`
  - `multi_llm_client.py`: Multi-AI integration (综合多个 AI 结果)
  - `example_usage.py`: minimal demo
  - `multi_llm_example.py`: multi-AI integration demo

This design ensures later provider changes require only environment changes, not code rewrites.