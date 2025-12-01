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

---

## Trading Idea & Strategy

### Why LLM-Based Trading?

Traditional algorithmic trading systems rely on hardcoded rules and statistical models. While effective, they often struggle with:
- **Context Understanding**: Interpreting complex market conditions that require nuanced judgment
- **Multi-Signal Integration**: Combining multiple technical indicators, market sentiment, and risk factors
- **Adaptability**: Adjusting strategies based on changing market regimes

We chose an **LLM-based approach** because modern language models excel at:
1. **Pattern Recognition**: Identifying subtle patterns across multiple data dimensions
2. **Reasoning**: Making logical connections between technical indicators, market conditions, and risk factors
3. **Natural Language Understanding**: Interpreting market data in a human-like way, considering context and nuance
4. **Structured Output**: Generating consistent, parseable JSON decisions while maintaining flexibility

### Strategy Selection Rationale

#### 1. **Multi-Currency Diversification Strategy**

**Why**: Instead of focusing solely on Bitcoin, we analyze all available trading pairs (60+ currencies) simultaneously.

**Benefits**:
- **Opportunity Maximization**: Increases the probability of finding profitable trades by scanning the entire market
- **Risk Diversification**: Reduces exposure to single-asset volatility
- **Comparative Analysis**: Allows agents to identify relative strength and select the best risk-reward opportunities

**Implementation**: Agents receive complete market snapshots with all trading pairs, enabling them to compare opportunities and select the optimal entry point.

#### 2. **Technical Analysis + LLM Interpretation**

**Why**: We combine quantitative technical indicators with LLM reasoning rather than using pure rule-based systems.

**Benefits**:
- **Indicator Interpretation**: LLMs can understand the *context* of technical signals (e.g., RSI > 70 in a strong uptrend vs. RSI > 70 after a sudden spike)
- **Multi-Signal Synthesis**: LLMs naturally integrate multiple indicators (EMA crossovers, MACD divergence, Bollinger Band position) into coherent trading decisions
- **Adaptive Logic**: LLMs can adjust their interpretation based on market conditions (e.g., being more cautious during high volatility)

**Technical Indicators Used**:
- **Trend Indicators**: EMA (9, 26, 50) for multi-timeframe trend identification
- **Momentum Indicators**: RSI (14) for overbought/oversold conditions
- **Volatility Indicators**: Bollinger Bands for volatility-based entry/exit signals
- **Trend Confirmation**: MACD for trend strength and momentum confirmation

#### 3. **Progressive Indicator Enhancement**

**Why**: We provide partial indicators immediately (with 2+ data points) and upgrade to full indicators as data accumulates.

**Benefits**:
- **Early Decision Capability**: Agents can make informed decisions even with limited historical data
- **Adaptive Analysis**: System automatically improves analysis quality as more data becomes available
- **No Dead Time**: Eliminates the "waiting period" where agents have no technical context

**Implementation**: 
- **Partial Indicators** (2-13 data points): Price trend, short-period EMAs/SMAs
- **Full Indicators** (14+ data points): RSI, MACD, Bollinger Bands, full EMA suite

#### 4. **Dual-Agent Architecture**

**Why**: Two independent agents with equal capital allocation operating in parallel.

**Benefits**:
- **Diversification of Decision-Making**: Different agents may identify different opportunities, reducing correlation risk
- **Redundancy**: If one agent makes a poor decision, the other can compensate
- **Competitive Analysis**: Agents can implicitly "compete" to find better opportunities

**Note**: Both agents use the same moderate risk profile, ensuring consistent risk management while maintaining decision diversity.

#### 5. **Confidence-Based Position Sizing**

**Why**: Position size scales with confidence level rather than using fixed sizes.

**Benefits**:
- **Risk-Reward Optimization**: Higher confidence trades justify larger positions
- **Capital Preservation**: Lower confidence trades use smaller positions, protecting capital
- **Adaptive Risk Management**: Automatically adjusts risk exposure based on signal quality

**Implementation**:
- 70-75% confidence → 1-1.5% risk (small positions)
- 75-85% confidence → 1.5-2% risk (normal positions)
- 85%+ confidence → up to 2% risk (larger positions, still capped)

---

## Technical Execution

### Architecture Design Principles

#### 1. **Modular Component Architecture**

**Design**: Each component (Market Collector, History Storage, Technical Indicators, Agents, Executor) operates independently with clear interfaces.

**Why**:
- **Maintainability**: Easy to update individual components without affecting others
- **Testability**: Each component can be tested in isolation
- **Scalability**: Can add more agents or indicators without major refactoring

**Implementation**:
- **Message Bus Pattern**: Components communicate via publish-subscribe message bus, ensuring loose coupling
- **Thread-Safe Operations**: All shared data structures use locks to prevent race conditions
- **Clear Interfaces**: Each component exposes well-defined methods and data structures

#### 2. **Real-Time Data Pipeline**

**Data Flow**:
```
Roostoo API → Market Collector → History Storage → Technical Indicators → Data Formatter → Agents → LLM → Executor → Roostoo API
```

**Key Design Decisions**:

- **Continuous Data Collection**: Market collector runs every 5 seconds, ensuring fresh data
- **Complete Snapshot Publishing**: Periodically publishes complete market snapshots (all pairs) rather than individual updates
- **Historical Data Persistence**: Every price update is stored (regardless of change) to build comprehensive datasets
- **Progressive Enhancement**: Technical indicators are calculated progressively as data accumulates

**Algorithm for Historical Data Storage**:
```python
# Pseudo-code
for each trading_pair:
    fetch_ticker_data()
    store_in_history_storage()  # Always store, regardless of price change
    update_last_tickers()       # Always update for complete snapshots
    if price_changed_significantly():
        publish_to_message_bus()  # Only publish if significant change
```

**Why Always Store**: Ensures all trading pairs accumulate historical data at the same rate, critical for accurate technical indicator calculation.

#### 3. **Technical Indicator Calculation Algorithms**

**EMA (Exponential Moving Average)**:
- Uses exponential weighting to give more weight to recent prices
- Formula: `EMA_today = (Price_today × α) + (EMA_yesterday × (1 - α))` where `α = 2 / (period + 1)`
- Calculated for periods: 3, 5, 9, 12, 26, 50

**RSI (Relative Strength Index)**:
- Measures momentum by comparing average gains vs. losses over 14 periods
- Formula: `RSI = 100 - (100 / (1 + RS))` where `RS = Average Gain / Average Loss`
- Values > 70 indicate overbought, < 30 indicate oversold

**MACD (Moving Average Convergence Divergence)**:
- Calculates difference between 12-period EMA and 26-period EMA
- Signal line: 9-period EMA of MACD line
- Histogram: Difference between MACD and signal line
- Used to identify trend changes and momentum shifts

**Bollinger Bands**:
- Upper/Lower bands: 20-period SMA ± (2 × standard deviation)
- Middle band: 20-period SMA
- Used to identify volatility and potential reversal points

**Partial Indicators Algorithm**:
```python
if data_count >= 2:
    calculate_price_trend()      # Simple up/down/flat
if data_count >= 3:
    calculate_sma_3()            # 3-period simple moving average
if data_count >= 5:
    calculate_sma_5()            # 5-period simple moving average
    calculate_ema_3()            # 3-period exponential moving average
# ... progressively add more indicators as data accumulates
```

#### 4. **LLM Decision Generation Pipeline**

**Process**:
1. **Market Data Formatting**: Converts raw market data + technical indicators into human-readable text
2. **Context Assembly**: Combines system prompt, market data, capital info, position info, and dialog history
3. **LLM Inference**: Sends formatted context to LLM (DeepSeek/Qwen) with temperature=0.7 for balanced creativity/consistency
4. **JSON Parsing**: Extracts structured decision from LLM output (handles both pure JSON and JSON wrapped in text)
5. **Validation**: Validates decision format and required fields

**Prompt Engineering Strategy**:
- **Structured Instructions**: Clear rules for decision-making, risk management, and output format
- **Context-Rich**: Includes all relevant market data, technical indicators, and account information
- **Multi-Currency Emphasis**: Explicitly instructs agents to analyze all available pairs
- **Risk-First Philosophy**: Emphasizes capital preservation and risk control throughout

**Rate Limiting Algorithm**:
```python
# Global rate limiter (shared between all agents)
GLOBAL_DECISION_RATE_LIMITER = RateLimiter(calls_per_minute=1)

# Each agent checks before generating decision
if not GLOBAL_DECISION_RATE_LIMITER.can_call():
    return  # Skip decision generation
GLOBAL_DECISION_RATE_LIMITER.record_call()
```

**Why Global Limiting**: Ensures the entire bot respects API rate limits, preventing excessive LLM calls.

#### 5. **Trade Execution Algorithm**

**Decision Parsing**:
1. **JSON Extraction**: Uses regex to find JSON in LLM output (handles wrapped JSON)
2. **Field Validation**: Checks for required fields (action, symbol, position_size_usd, etc.)
3. **Symbol Normalization**: Converts symbol format (e.g., "BTCUSDT" → "BTC/USD")
4. **Position Size Validation**: Ensures position size doesn't exceed available capital

**Execution Flow**:
```python
if action == "open_long":
    calculate_quantity = position_size_usd / current_price
    place_buy_order(symbol, quantity)
    update_position_tracker()
elif action == "close_long":
    get_current_holdings(symbol)
    place_sell_order(symbol, quantity)
    update_position_tracker()
```

**Error Handling**:
- API failures: Logs error, continues operation (doesn't crash)
- Invalid decisions: Logs warning, skips execution
- Rate limit violations: Waits and retries

---

## Risk Management & Controls

### Multi-Layered Risk Control Philosophy

We implement **defense-in-depth** risk management: multiple independent layers of protection, so if one layer fails, others still protect capital.

### Layer 1: Pre-Trade Risk Controls

#### 1. **Confidence Threshold System**

**Control**: Agents only trade when confidence ≥ 70%.

**Why**:
- **Quality Over Quantity**: Prevents low-quality trades that erode capital through fees and small losses
- **Signal Quality Filter**: Higher confidence typically correlates with stronger technical signals
- **Capital Preservation**: Waiting for better opportunities preserves capital for high-probability setups

**Implementation**:
- Confidence < 70% → `wait` action
- Confidence 70-75% → Small positions (1-1.5% risk)
- Confidence 75-85% → Normal positions (1.5-2% risk)
- Confidence 85%+ → Larger positions (up to 2% risk limit)

#### 2. **Position Sizing Limits**

**Control**: Maximum 2% of account equity risked per trade.

**Why**:
- **Drawdown Control**: Limits maximum loss per trade, preventing catastrophic single-trade losses
- **Mathematical Safety**: Even with 10 consecutive losses, total drawdown would be < 20%
- **Capital Preservation**: Ensures sufficient capital remains for future opportunities

**Calculation**:
```
Risk Amount = Position Size × (Entry Price - Stop Loss Price) / Entry Price
Risk Amount ≤ 2% of Account Equity
```

#### 3. **Minimum Risk-Reward Ratio**

**Control**: Minimum 2.5:1 risk-reward ratio (after accounting for 0.2% trading fees).

**Why**:
- **Fee Compensation**: Ensures profits exceed trading costs (0.1% buy + 0.1% sell = 0.2% total)
- **Expected Value**: Positive expected value over many trades
- **Profitability Requirement**: Only trades with favorable risk-reward are executed

**Example**:
- Entry: $100,000
- Stop Loss: $98,000 (2% risk)
- Take Profit: $105,000 (5% reward)
- Risk-Reward: 5% / 2% = 2.5:1 ✓

#### 4. **Cooling Periods**

**Control**: Minimum time intervals between trades.

**Why**:
- **Overtrading Prevention**: Prevents emotional or reactive trading after wins/losses
- **Market Regime Changes**: Allows time for market conditions to evolve
- **Decision Quality**: Forces agents to wait and reconsider before new trades

**Rules**:
- After opening position: ≥ 5-6 minutes before next trade
- After closing position: ≥ 4 minutes (stop-loss) or ≥ 2 minutes (take-profit)
- If holding position: ≥ 20 minutes before closing

### Layer 2: In-Trade Risk Controls

#### 1. **Stop-Loss Orders**

**Control**: Every trade includes a predefined stop-loss level.

**Why**:
- **Loss Limitation**: Caps maximum loss per trade
- **Emotional Discipline**: Removes emotion from exit decisions
- **Capital Protection**: Prevents small losses from becoming large losses

**Implementation**: Stop-loss is set at trade entry and executed automatically if price reaches the level.

#### 2. **Take-Profit Orders**

**Control**: Every trade includes a predefined take-profit level.

**Why**:
- **Profit Locking**: Secures profits when targets are reached
- **Greed Prevention**: Prevents holding winners too long and watching profits disappear
- **Risk-Reward Realization**: Ensures the planned risk-reward ratio is achieved

#### 3. **Trailing Stop-Loss (Profit Protection)**

**Control**: Stop-loss is adjusted upward as price moves favorably.

**Why**:
- **Profit Protection**: Locks in profits as trades move in favor
- **Trend Following**: Allows profits to run while protecting gains
- **Drawdown Reduction**: Reduces maximum drawdown by protecting accumulated profits

**Rules**:
- Profit > 2.5% → Move stop-loss to entry (breakeven, accounting for fees)
- Profit > 5% → Move stop-loss to entry + 1%
- Profit > 10% → Move stop-loss to entry + 3%

#### 4. **Partial Position Closing**

**Control**: Close 50% of position when profit targets (5-8%) are reached.

**Why**:
- **Profit Locking**: Secures partial profits while allowing remaining position to continue
- **Risk Reduction**: Reduces exposure while maintaining upside potential
- **Drawdown Control**: Protects against reversals that could erase all profits

### Layer 3: Portfolio-Level Risk Controls

#### 1. **Consecutive Loss Limits**

**Control**: Trading pauses after consecutive losses.

**Why**:
- **Emotional Trading Prevention**: Stops trading when agents may be making poor decisions
- **Market Regime Recognition**: Acknowledges that market conditions may have changed
- **Capital Preservation**: Prevents continued losses during unfavorable periods

**Rules**:
- 2 consecutive losses → Pause 30 minutes
- 3 consecutive losses → Pause 18 hours
- 4 consecutive losses → Pause 48 hours

#### 2. **Daily Loss Limits**

**Control**: Stop trading if daily loss exceeds 3% of account equity.

**Why**:
- **Drawdown Control**: Prevents catastrophic daily losses
- **Calmar Ratio Protection**: Protects against large drawdowns that hurt risk-adjusted returns
- **Circuit Breaker**: Acts as a safety net if other controls fail

#### 3. **Maximum Drawdown Controls**

**Control**: Reduce position sizes or stop trading if drawdown exceeds thresholds.

**Why**:
- **Capital Preservation**: Protects remaining capital during difficult periods
- **Recovery Focus**: Allows time for portfolio to recover before resuming normal trading
- **Risk-Adjusted Returns**: Improves Calmar Ratio by limiting maximum drawdown

**Rules**:
- Drawdown > 3% → Reduce position sizes, only trade with >85% confidence
- Drawdown > 5% → Stop trading, wait for recovery

#### 4. **Performance-Based Risk Adjustment**

**Control**: Adjust risk based on Sortino, Sharpe, and Calmar ratios.

**Why**:
- **Adaptive Risk Management**: Reduces risk when performance metrics deteriorate
- **Competition Optimization**: Aligns with competition evaluation criteria (Sortino 40%, Sharpe 30%, Calmar 30%)
- **Dynamic Response**: Responds to changing market conditions and performance

**Rules**:
- **Sortino < -0.5**: Pause 15 minutes
- **Sharpe < -0.5**: Pause 15 minutes
- **Calmar < -1.0**: Pause 30 minutes
- **All ratios negative**: Only trade with >85% confidence

### Layer 4: Operational Risk Controls

#### 1. **Rate Limiting**

**Control**: Maximum 1 decision per minute (global, shared between agents).

**Why**:
- **API Compliance**: Respects Roostoo API rate limits
- **LLM Cost Control**: Limits expensive LLM API calls
- **Decision Quality**: Prevents rushed decisions, encourages thoughtful analysis

#### 2. **Error Handling & Resilience**

**Control**: System continues operating even if individual components fail.

**Why**:
- **Uptime**: Ensures bot continues operating during temporary API failures
- **Data Integrity**: Prevents data corruption from partial failures
- **Graceful Degradation**: System degrades gracefully rather than crashing

**Implementation**:
- Try-catch blocks around all API calls
- Logging of all errors for debugging
- Fallback behaviors (e.g., skip trade if API fails, continue collecting data)

#### 3. **Data Validation**

**Control**: Validates all market data and decisions before use.

**Why**:
- **Garbage In, Garbage Out Prevention**: Prevents bad data from causing bad decisions
- **System Stability**: Prevents crashes from unexpected data formats
- **Decision Quality**: Ensures only valid, well-formed decisions are executed

### Risk Control Summary

| Control Layer | Controls | Purpose |
|--------------|----------|---------|
| **Pre-Trade** | Confidence thresholds, position sizing, risk-reward ratio, cooling periods | Prevent bad trades before they happen |
| **In-Trade** | Stop-loss, take-profit, trailing stops, partial closes | Manage risk during open positions |
| **Portfolio** | Consecutive loss limits, daily loss limits, drawdown controls, performance-based adjustment | Protect overall portfolio health |
| **Operational** | Rate limiting, error handling, data validation | Ensure system reliability and compliance |

### Why These Controls?

1. **Competition Alignment**: Controls are optimized for competition evaluation metrics (Sortino 40%, Sharpe 30%, Calmar 30%)
2. **Capital Preservation**: Multiple layers ensure capital is protected even if individual controls fail
3. **Adaptive Response**: Controls adjust based on performance, preventing continued losses during difficult periods
4. **Mathematical Foundation**: Position sizing and risk-reward ratios are based on mathematical principles (Kelly Criterion, expected value)
5. **Psychological Discipline**: Cooling periods and loss limits prevent emotional trading decisions

---

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
