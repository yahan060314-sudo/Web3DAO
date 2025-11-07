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
# Select provider: deepseek | qwen
LLM_PROVIDER=deepseek

# DeepSeek Configuration
DEEPSEEK_API_KEY=sk-your-actual-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com  # Also supports: https://api.deepseek.com/v1 (OpenAI compatible)
DEEPSEEK_MODEL=deepseek-chat  # Options: deepseek-chat (recommended), deepseek-reasoner, or deepseek-coder

# Qwen (AKA DashScope)
QWEN_API_KEY=your_qwen_api_key
QWEN_BASE_URL=https://api.qwen.ai
QWEN_MODEL=qwen-chat

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

## Structure

- `api/roostoo_client.py`: Roostoo REST client
- `api/data_fetcher.py`: polling example against Roostoo
- `api/llm_clients/`: provider-agnostic LLM interface
  - `base.py`: `LLMClient` interface
  - `deepseek_client.py`, `qwen_client.py`: concrete implementations
  - `factory.py`: selects provider via `LLM_PROVIDER`
  - `example_usage.py`: minimal demo

This design ensures later provider changes require only environment changes, not code rewrites.