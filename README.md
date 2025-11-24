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

## Running the Trading Bot

### Production Mode

Run the bot in production mode (connects to real Roostoo API):

```bash
python run_bot.py
```

### Test Mode

Run the bot in test mode (connects to mock Roostoo API):

```bash
python run_bot_test.py
```

### Running in tmux (Recommended for Long-term Operation)

```bash
# Create a new tmux session
tmux new-session -d -s trading_bot 'python run_bot.py'

# Attach to the session to view logs
tmux attach -t trading_bot

# Detach from session (press Ctrl+B, then D)

# Stop the bot
tmux kill-session -t trading_bot
```

## Strategy Documentation

### Core Idea

Our trading bot implements a **dual-agent LLM-based trading system** that leverages Large Language Models (LLMs) to make intelligent trading decisions in cryptocurrency markets. The core philosophy is to combine:

1. **Technical Analysis**: Real-time calculation of technical indicators (EMA, MACD, RSI, Bollinger Bands) from historical price data
2. **LLM Reasoning**: Using advanced LLMs (DeepSeek/Qwen) to analyze market conditions, interpret technical indicators, and make nuanced trading decisions
3. **Risk Management**: Multi-layered risk control including position sizing, stop-loss, take-profit, and cooling periods
4. **Multi-Currency Strategy**: Analyzing all available trading pairs simultaneously to identify the best opportunities

### Architecture Overview

The system consists of several key components working together:

```
┌─────────────────┐
│ Market Collector│ → Collects real-time market data (prices, volumes)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ History Storage │ → Stores historical price data for technical indicators
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Technical       │ → Calculates EMA, MACD, RSI, Bollinger Bands
│ Indicators      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Data Formatter  │ → Formats market data + indicators for LLM consumption
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌─────────────────┐
│   Agent 1       │      │   Agent 2       │ → Two independent agents
│  (Moderate)     │      │  (Moderate)     │   analyzing market data
└────────┬────────┘      └────────┬────────┘
         │                        │
         └──────────┬─────────────┘
                    ▼
         ┌─────────────────┐
         │  LLM (DeepSeek/  │ → Generates trading decisions
         │      Qwen)       │   based on analysis
         └────────┬─────────┘
                  │
                  ▼
         ┌─────────────────┐
         │ Trade Executor  │ → Executes trades via Roostoo API
         └─────────────────┘
```

### Implementation Details

#### 1. Market Data Collection (`market_collector.py`)

- **Continuous Data Collection**: Periodically fetches ticker data for all available trading pairs (every 5 seconds)
- **Historical Data Storage**: Stores every price update in `HistoryStorage` (regardless of price change) to build comprehensive historical datasets
- **Complete Market Snapshots**: Periodically publishes complete market snapshots containing all trading pairs, enabling agents to compare opportunities across all currencies

#### 2. Technical Indicators (`technical_indicators.py`, `history_storage.py`)

- **Full Indicators** (requires 14+ data points):
  - **RSI (14)**: Relative Strength Index for momentum analysis
  - **EMA (9, 26, 50)**: Exponential Moving Averages for trend identification
  - **MACD**: Moving Average Convergence Divergence with signal line and histogram
  - **Bollinger Bands**: Upper, middle, and lower bands for volatility analysis

- **Partial Indicators** (available with 2+ data points):
  - **Price Trend**: Simple trend direction (up/down/flat) with percentage change
  - **SMA (3, 5)**: Short-period Simple Moving Averages
  - **EMA (3, 5, 9, 12)**: Short-period Exponential Moving Averages

- **Progressive Enhancement**: The system provides partial indicators immediately (even with limited data) and automatically upgrades to full indicators as more historical data accumulates

#### 3. LLM-Based Decision Making (`base_agent.py`)

- **Dual Agent System**: Two independent agents operate in parallel, each with equal capital allocation
- **Decision Process**:
  1. Receives complete market snapshot with technical indicators
  2. Analyzes all available trading pairs simultaneously
  3. Uses LLM to interpret technical signals, market conditions, and risk factors
  4. Generates structured JSON decision with action, symbol, position size, stop-loss, take-profit, and reasoning
- **Rate Limiting**: Global rate limiter ensures the entire bot makes at most 1 decision per minute (shared between both agents)
- **Prompt Engineering**: Uses sophisticated prompts (`natural_language_prompt.txt`) that emphasize:
  - Multi-currency analysis
  - Risk-reward ratio evaluation
  - Confidence-based position sizing
  - Cooling periods and risk management rules

#### 4. Risk Management (`position_tracker.py`, `capital_manager.py`)

- **Position Tracking**: Tracks USD balance and cryptocurrency holdings for each agent
- **Capital Allocation**: Equal capital distribution between agents at startup
- **Position Sizing**: Based on confidence level and risk profile:
  - 70-75% confidence: Small positions (1-1.5% risk)
  - 75-85% confidence: Normal positions (1.5-2% risk)
  - 85%+ confidence: Larger positions (up to 2% risk limit)
- **Cooling Periods**: Enforces minimum time intervals between trades to prevent overtrading
- **Stop-Loss & Take-Profit**: Every trade includes predefined risk management parameters

#### 5. Trade Execution (`executor.py`)

- **JSON Decision Parsing**: Parses structured JSON decisions from LLM output
- **API Integration**: Executes trades via Roostoo API with proper authentication
- **Rate Limiting**: Respects 1 trade per minute limit
- **Position Management**: Handles both opening new positions and closing existing ones

### Key Features

1. **Multi-Currency Analysis**: Agents analyze all available trading pairs (60+ currencies) simultaneously, not just Bitcoin
2. **Adaptive Technical Analysis**: Provides partial indicators immediately and full indicators as data accumulates
3. **LLM Reasoning**: Leverages advanced LLMs to interpret complex market conditions and make nuanced decisions
4. **Structured Output**: LLM decisions are in structured JSON format, ensuring reliable parsing and execution
5. **Risk-First Approach**: Multiple layers of risk control including confidence thresholds, cooling periods, and position limits
6. **Provider Agnostic**: Can switch between DeepSeek, Qwen, and Minimax by changing environment variables

### Decision-Making Philosophy

The bot follows a **balanced risk-reward approach**:

- **70%+ Confidence**: Agents are encouraged to take positions when they have reasonable confidence
- **<70% Confidence**: Agents wait for better opportunities
- **Risk Control**: Every trade must have stop-loss and take-profit levels
- **Multi-Signal Validation**: Agents consider multiple factors: technical indicators, price trends, volume, and risk-reward ratios
- **Capital Preservation**: Strict position sizing and cooling periods prevent excessive risk-taking

This approach balances the need to capture opportunities with the imperative to preserve capital and manage risk effectively.

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
- `api/agents/`: Trading bot agents and components
  - `base_agent.py`: Core agent implementation with LLM decision-making
  - `market_collector.py`: Market data collection and publishing
  - `history_storage.py`: Historical price data storage
  - `technical_indicators.py`: Technical indicator calculations
  - `data_formatter.py`: Market data formatting for LLM consumption
  - `executor.py`: Trade execution via Roostoo API
  - `position_tracker.py`: Position and balance tracking
  - `capital_manager.py`: Capital allocation and management
  - `prompt_manager.py`: Prompt template management
- `run_bot.py`: Main entry point for production mode
- `run_bot_test.py`: Main entry point for test mode
- `prompts/`: LLM prompt templates
  - `natural_language_prompt.txt`: Main trading strategy prompt

This design ensures later provider changes require only environment changes, not code rewrites.
