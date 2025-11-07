# AI Agent 交易系统架构文档

## 概述

这是一个模块化的Web3量化交易系统，通过AI Agent分析市场数据并做出交易决策。

## 系统架构

```
┌─────────────────┐
│ Roostoo API     │ 市场数据源
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ MarketData       │ 数据采集器
│ Collector        │ (定期获取数据)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ DataFormatter    │ 数据格式化
│                  │ (转换为结构化格式)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ MessageBus      │ 消息总线
│ (发布/订阅)     │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌─────────┐
│ Agent 1 │ │ Agent 2 │ AI Agents
│         │ │         │ (分析决策)
└────┬────┘ └────┬────┘
     │           │
     └─────┬─────┘
           │
           ▼
    ┌──────────────┐
    │ TradeExecutor│ 交易执行器
    │              │ (执行交易)
    └──────────────┘
```

## 核心模块说明

### 1. MarketDataCollector (市场数据采集器)

**位置**: `api/agents/market_collector.py`

**功能**:
- 独立线程运行，定期从Roostoo API获取市场数据
- 支持采集ticker（价格行情）和balance（账户余额）
- 自动将数据发布到消息总线

**使用示例**:
```python
from api.agents.market_collector import MarketDataCollector
from api.agents.bus import MessageBus

bus = MessageBus()
collector = MarketDataCollector(
    bus=bus,
    market_topic="market_ticks",
    pairs=["BTC/USD", "ETH/USD"],  # 要监控的交易对
    collect_interval=5.0,  # 每5秒采集一次
    collect_balance=True,
    collect_ticker=True
)
collector.start()
```

### 2. DataFormatter (数据格式化器)

**位置**: `api/agents/data_formatter.py`

**功能**:
- 将Roostoo API返回的原始数据格式化为统一的结构
- 提取关键市场指标（价格、成交量、涨跌幅等）
- 格式化账户信息
- 提供LLM可读的文本格式

**数据格式**:

**Ticker数据**:
```python
{
    "type": "ticker",
    "pair": "BTC/USD",
    "price": 45000.0,
    "volume_24h": 1234567.89,
    "change_24h": 2.5,
    "high_24h": 46000.0,
    "low_24h": 44000.0,
    "timestamp": 1234567890.0
}
```

**Balance数据**:
```python
{
    "type": "balance",
    "total_balance": 10000.0,
    "available_balance": 8000.0,
    "currencies": {
        "USD": {"available": 8000.0, "locked": 0.0, "total": 8000.0},
        "BTC": {"available": 0.1, "locked": 0.0, "total": 0.1}
    }
}
```

**使用示例**:
```python
from api.agents.data_formatter import DataFormatter

formatter = DataFormatter()
formatted_ticker = formatter.format_ticker(raw_ticker_data, pair="BTC/USD")
formatted_balance = formatter.format_balance(raw_balance_data)

# 创建综合市场快照
snapshot = formatter.create_market_snapshot(
    ticker=formatted_ticker,
    balance=formatted_balance
)

# 格式化为LLM可读文本
llm_text = formatter.format_for_llm(snapshot)
```

### 3. PromptManager (Prompt管理器)

**位置**: `api/agents/prompt_manager.py`

**功能**:
- 管理AI Agent的系统提示词
- 创建基于市场数据的交易提示词
- 支持动态prompt生成
- 提供预定义的prompt模板

**使用示例**:
```python
from api.agents.prompt_manager import PromptManager

pm = PromptManager()

# 获取系统提示词
system_prompt = pm.get_system_prompt(
    agent_name="TradingAgent",
    trading_strategy="Focus on trend following",
    risk_level="moderate"  # conservative/moderate/aggressive
)

# 创建交易提示词
trading_prompt = pm.create_trading_prompt(
    market_snapshot=snapshot,
    additional_context="Market is volatile today"
)

# 使用预定义模板
template = pm.get_template("risk_assessment")
custom_prompt = pm.create_custom_prompt(
    template,
    volatility="high",
    balance=10000.0,
    positions=2
)
```

### 4. BaseAgent (基础Agent)

**位置**: `api/agents/base_agent.py`

**功能**:
- 订阅市场数据和对话消息
- 使用LLM生成交易决策
- 发布决策到消息总线
- 自动聚合市场数据

**改进**:
- ✅ 使用DataFormatter格式化市场数据
- ✅ 支持结构化的市场数据（ticker、balance等）
- ✅ 自动聚合多个数据源
- ✅ 定期自动生成决策

### 5. AgentManager (Agent管理器)

**位置**: `api/agents/manager.py`

**功能**:
- 创建和管理多个Agent
- 广播市场数据和prompt
- 收集Agent决策

### 6. TradeExecutor (交易执行器)

**位置**: `api/agents/executor.py`

**功能**:
- 订阅Agent决策
- 解析自然语言决策
- 执行实际交易（遵守限频规则）

## 数据流说明

### 1. 市场数据流

```
Roostoo API 
  → MarketDataCollector (采集)
  → DataFormatter (格式化)
  → MessageBus (发布到 "market_ticks" topic)
  → BaseAgent (订阅并接收)
  → Agent内部聚合为market_snapshot
```

### 2. Prompt流

```
PromptManager (创建prompt)
  → AgentManager.broadcast_prompt()
  → MessageBus (发布到 "dialog_prompts" topic)
  → BaseAgent (订阅并接收)
  → Agent生成决策
```

### 3. 决策流

```
BaseAgent (生成决策)
  → MessageBus (发布到 "decisions" topic)
  → TradeExecutor (订阅并执行)
  → Roostoo API (下单)
```

## 使用示例

### 完整集成示例

运行完整系统：
```bash
python -m api.agents.integrated_example
```

这个示例展示了：
1. 创建多个Agent（保守型、平衡型）
2. 启动市场数据采集器
3. 启动交易执行器
4. 定期发送交易提示
5. 收集和显示决策

### 自定义使用

```python
from api.agents.manager import AgentManager
from api.agents.market_collector import MarketDataCollector
from api.agents.prompt_manager import PromptManager
from api.agents.executor import TradeExecutor

# 1. 初始化
mgr = AgentManager()
pm = PromptManager()

# 2. 创建Agent
system_prompt = pm.get_system_prompt(
    agent_name="MyAgent",
    risk_level="moderate"
)
mgr.add_agent(name="my_agent", system_prompt=system_prompt)
mgr.start()

# 3. 启动数据采集
collector = MarketDataCollector(
    bus=mgr.bus,
    market_topic=mgr.market_topic,
    pairs=["BTC/USD"],
    collect_interval=5.0
)
collector.start()

# 4. 启动执行器
executor = TradeExecutor(
    bus=mgr.bus,
    decision_topic=mgr.decision_topic
)
executor.start()

# 5. 发送交易提示
snapshot = collector.get_latest_snapshot()
trading_prompt = pm.create_trading_prompt(snapshot)
mgr.broadcast_prompt(role="user", content=trading_prompt)
```

## 模块化设计优势

1. **数据采集独立**: MarketDataCollector可以独立运行，不影响Agent逻辑
2. **数据格式化统一**: DataFormatter确保所有Agent看到相同格式的数据
3. **Prompt管理灵活**: PromptManager方便组友扩展和修改prompt
4. **Agent可扩展**: BaseAgent可以被子类化，实现特定策略
5. **消息总线解耦**: 各模块通过消息总线通信，互不依赖

## 扩展指南

### 添加新的数据源

1. 在`DataFormatter`中添加新的格式化方法
2. 在`MarketDataCollector`中添加采集逻辑
3. 发布到消息总线

### 添加新的Prompt类型

1. 在`PromptManager`中添加新方法
2. 或使用`create_custom_prompt`和模板

### 创建自定义Agent

```python
from api.agents.base_agent import BaseAgent

class MyCustomAgent(BaseAgent):
    def _generate_decision(self, user_prompt: str):
        # 自定义决策逻辑
        super()._generate_decision(user_prompt)
```

## 注意事项

1. **API限频**: Roostoo API有请求频率限制，MarketDataCollector的`collect_interval`不要设置太小
2. **交易限频**: TradeExecutor遵守`TRADE_INTERVAL_SECONDS`（61秒）的限制
3. **数据格式**: 如果Roostoo API返回格式变化，需要更新`DataFormatter`
4. **Prompt长度**: Agent的对话历史会控制长度，避免超出LLM token限制

## 故障排查

1. **没有市场数据**: 检查MarketDataCollector是否启动，Roostoo API是否正常
2. **Agent没有决策**: 检查prompt是否正确发送，LLM API是否正常
3. **交易未执行**: 检查TradeExecutor是否启动，决策格式是否正确

