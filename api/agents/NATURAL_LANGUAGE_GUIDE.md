# 自然语言交流指南

## 概述

本系统使用**自然语言**与AI Agent进行交流。所有交互都是通过文本（自然语言）完成的。

## 自然语言交流的三个层面

### 1. 系统提示词（System Prompt）- 定义Agent角色

**位置**: `api/agents/prompt_manager.py` 的 `get_system_prompt()` 方法

**作用**: 告诉Agent它是什么角色，应该怎么工作

**示例**:
```python
from api.agents.prompt_manager import PromptManager

pm = PromptManager()
system_prompt = pm.get_system_prompt(
    agent_name="TradingAgent",
    trading_strategy="Focus on trend following",
    risk_level="moderate"
)
```

**实际生成的文本**（自然语言）:
```
You are TradingAgent, an AI trading assistant for Web3 quantitative trading.

Your responsibilities:
1. Analyze real-time market data (prices, volumes, trends)
2. Monitor account balance and available funds
3. Make trading decisions based on market conditions
4. Consider risk management in all decisions

Risk Level: moderate

Risk Guidelines: Balance risk and reward. Look for good opportunities but don't take excessive risks.

When making decisions, provide clear reasoning:
- What market signals you're seeing
- Why you're making this decision
- Expected outcome and risk assessment

Format your decisions as:
- "buy [quantity] [pair]" for market buy orders
- "sell [quantity] [pair]" for market sell orders  
- "buy [quantity] [pair] at [price]" for limit buy orders
- "sell [quantity] [pair] at [price]" for limit sell orders
- "hold" if no action is recommended

Be concise but informative.
```

### 2. 用户提示词（User Prompt）- 给Agent的指令

**位置**: `api/agents/prompt_manager.py` 的 `create_trading_prompt()` 方法

**作用**: 告诉Agent当前要做什么任务

**示例**:
```python
trading_prompt = pm.create_trading_prompt(
    market_snapshot=snapshot,
    additional_context="Market is volatile today"
)
```

**实际生成的文本**（自然语言）:
```
Analyze the current market situation and make a trading decision.

📊 Market Data (BTC/USD):
  Current Price: $45000.00
  24h Change: +2.50%
  24h Volume: 1234567.89
  24h Range: $44000.00 - $46000.00

💰 Account Balance:
  Total Balance: $10000.00
  Available: $8000.00
  Currencies:
    USD: 8000.0000 (Available: 8000.0000)
    BTC: 0.1000 (Available: 0.1000)

Additional Context: Market is volatile today

Based on the above information:
1. What is your analysis of the current market?
2. What trading action do you recommend?
3. What is your reasoning?

Provide your decision in the format specified in your system prompt.
```

### 3. Agent回复（Agent Response）- LLM生成的决策

**位置**: `api/agents/base_agent.py` 的 `_generate_decision()` 方法

**作用**: Agent分析后返回的自然语言决策

**实际生成的文本**（自然语言）:
```
Based on the current market analysis:
- BTC/USD is at $45,000, showing a positive 2.5% increase in 24h
- Volume is healthy at 1.23M, indicating active trading
- Price is in the middle of the 24h range ($44k-$46k), suggesting stability
- Account has $8,000 available for trading

Recommendation: buy 0.01 BTC/USD

Reasoning: 
The upward trend (2.5% gain) combined with healthy volume suggests continued momentum. 
The price is not at extremes, providing a reasonable entry point. 
With $8,000 available, a 0.01 BTC position represents about 4.5% of available capital, 
which aligns with moderate risk management.

Risk assessment: Moderate - The trend is positive but market volatility mentioned 
in context requires careful monitoring. Consider setting a stop loss at $44,500.
```

## 完整交互流程

```
1. 系统启动
   ↓
2. 创建Agent（使用系统提示词定义角色）
   System Prompt: "You are TradingAgent..."
   ↓
3. 市场数据采集
   Raw Data → DataFormatter → 自然语言文本
   "📊 Market Data (BTC/USD): Current Price: $45000..."
   ↓
4. 创建用户提示词
   User Prompt: "Analyze the current market situation..."
   ↓
5. 发送给Agent
   MessageBus → BaseAgent接收
   ↓
6. Agent处理
   LLM分析 → 生成自然语言决策
   ↓
7. Agent回复
   "Recommendation: buy 0.01 BTC/USD. Reasoning: ..."
   ↓
8. 执行器解析
   TradeExecutor解析自然语言 → 执行交易
```

## 代码位置总结

| 组件 | 文件 | 方法 | 说明 |
|------|------|------|------|
| 系统提示词 | `prompt_manager.py` | `get_system_prompt()` | 定义Agent角色 |
| 用户提示词 | `prompt_manager.py` | `create_trading_prompt()` | 创建交易指令 |
| 市场数据格式化 | `data_formatter.py` | `format_for_llm()` | 数据转自然语言 |
| Agent决策生成 | `base_agent.py` | `_generate_decision()` | LLM生成决策 |
| 消息传递 | `base_agent.py` | `_handle_dialog()` | 接收自然语言提示 |

## 自然语言示例

### 输入示例（给Agent的）

```
Analyze the current market situation and make a trading decision.

📊 Market Data (BTC/USD):
  Current Price: $45000.00
  24h Change: +2.50%
  24h Volume: 1234567.89
  24h Range: $44000.00 - $46000.00

💰 Account Balance:
  Total Balance: $10000.00
  Available: $8000.00

Based on the above information:
1. What is your analysis of the current market?
2. What trading action do you recommend?
3. What is your reasoning?
```

### 输出示例（Agent回复的）

```
Market Analysis:
- BTC/USD is showing positive momentum with 2.5% gain
- Volume is healthy, indicating strong interest
- Price is in middle range, not at extremes
- Account has sufficient funds for trading

Recommendation: buy 0.01 BTC/USD

Reasoning: The upward trend and healthy volume suggest continued momentum. 
Entry at current level provides good risk/reward ratio.

Risk: Moderate - monitor for any reversal signals.
```

## 关键点

1. **所有交流都是自然语言**：没有结构化API调用，都是文本对话
2. **数据自动格式化**：市场数据自动转换为自然语言描述
3. **LLM理解自然语言**：Agent可以理解复杂的指令和上下文
4. **决策也是自然语言**：Agent的回复是完整的分析文本，不是简单的"buy/sell"

## 运行示例

查看具体使用情况：
```bash
python -m api.agents.simple_example
```

这个示例会展示：
- 系统提示词的实际文本
- 用户提示词的实际文本
- Agent回复的示例格式
- 完整的交互流程

