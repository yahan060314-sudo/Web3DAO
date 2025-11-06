# Web3DAO

LLM provider-agnostic client layer for DeepSeek/Qwen integration, aligned with Roostoo trading bot.

## Quick Start

1) Create a `.env` at project root with any provider you want to use later:

```
# Select provider: deepseek | qwen
LLM_PROVIDER=deepseek

# DeepSeek
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# Qwen (AKA DashScope)
QWEN_API_KEY=your_qwen_api_key
QWEN_BASE_URL=https://api.qwen.ai
QWEN_MODEL=qwen-chat

# Roostoo credentials (already used by api/roostoo_client.py)
ROOSTOO_API_KEY=your_roostoo_api_key
ROOSTOO_SECRET_KEY=your_roostoo_secret
```

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