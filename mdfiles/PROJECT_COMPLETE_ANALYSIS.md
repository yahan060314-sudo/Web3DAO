# Web3DAO 项目完整流程分析文档

## 目录
1. [项目概述](#项目概述)
2. [系统架构](#系统架构)
3. [完整数据流](#完整数据流)
4. [Agent详细操作流程](#agent详细操作流程)
5. [Prompt系统详解](#prompt系统详解)
6. [Rate Limit机制](#rate-limit机制)
7. [策略强度配置](#策略强度配置)
8. [关键文件说明](#关键文件说明)

---

## 项目概述

这是一个基于AI Agent的Web3量化交易系统，通过多个AI Agent分析市场数据并做出交易决策，最终通过Roostoo API执行真实交易。

**核心特性：**
- 双Agent架构：两个Agent平分本金，独立决策
- 消息总线架构：模块间通过消息总线解耦通信
- 多LLM支持：支持DeepSeek、Qwen、Minimax等LLM提供商
- 频率限制：API调用和决策生成都有严格的频率限制
- 真实交易：支持真实交易和测试模式（dry_run）

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     运行入口                                  │
│  run_bot.py / run_production.py                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  AgentManager (管理器)                       │
│  文件: api/agents/manager.py                                │
│  - 创建和管理多个Agent                                       │
│  - 广播市场数据和prompt                                      │
│  - 收集Agent决策                                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌──────────────┐            ┌──────────────────┐
│ MessageBus   │            │ CapitalManager    │
│ (消息总线)   │            │ (资金管理器)      │
│ bus.py       │            │ capital_manager.py│
└──────┬───────┘            └──────────────────┘
       │
       ├─────────────────────────────────────────┐
       │                                         │
       ▼                                         ▼
┌──────────────────┐                  ┌──────────────────┐
│ MarketData       │                  │ BaseAgent        │
│ Collector        │                  │ (AI Agent)      │
│ market_collector │                  │ base_agent.py    │
│ .py              │                  │                  │
└──────┬───────────┘                  └────────┬─────────┘
       │                                        │
       │ 发布市场数据                            │ 发布决策
       │                                        │
       ▼                                        ▼
┌──────────────────┐                  ┌──────────────────┐
│ DataFormatter    │                  │ TradeExecutor     │
│ data_formatter.py│                  │ executor.py      │
└──────────────────┘                  └────────┬─────────┘
                                                │
                                                ▼
                                       ┌──────────────────┐
                                       │ RoostooClient    │
                                       │ roostoo_client.py│
                                       └──────────────────┘
```

---

## 完整数据流

### 1. 市场数据采集流程

**文件位置：** `api/agents/market_collector.py`

```
Roostoo API
    │
    ▼
MarketDataCollector.run() [独立线程]
    │
    ├─ _collect_tickers() [每12秒]
    │   │
    │   ├─ RoostooClient.get_ticker(pair)
    │   │   └─ 使用 API_RATE_LIMITER 限制频率
    │   │
    │   └─ DataFormatter.format_ticker(raw_ticker, pair)
    │       └─ 返回格式化的ticker数据
    │
    └─ _collect_balance() [每12秒]
        │
        ├─ RoostooClient.get_balance()
        │   └─ 使用 API_RATE_LIMITER 限制频率
        │
        └─ DataFormatter.format_balance(raw_balance)
            └─ 返回格式化的balance数据
    │
    ▼
MessageBus.publish(market_topic, formatted_data)
    │
    ▼
BaseAgent.market_sub.recv() [订阅市场数据]
    │
    ▼
BaseAgent._handle_market_data(msg)
    │
    ├─ 更新 self.current_tickers[pair] = msg
    ├─ 更新 self.current_balance = msg
    │
    └─ 创建市场快照
        DataFormatter.create_market_snapshot(ticker, balance)
            └─ 保存到 self.last_market_snapshot
```

**关键配置：**
- 采集间隔：`collect_interval=12.0` 秒（在 `run_bot.py` 第339行设置）
- 频率限制：每分钟最多5次API调用（`utils/rate_limiter.py` 第87行）

### 2. Prompt生成和传递流程

**文件位置：** `api/agents/prompt_manager.py`

```
PromptManager.create_trading_prompt()
    │
    ├─ 输入: market_snapshot (来自MarketDataCollector)
    ├─ 输入: additional_context (可选)
    ├─ 输入: require_decision (是否强制要求决策)
    │
    ├─ DataFormatter.format_for_llm(snapshot)
    │   └─ 将市场快照转换为LLM可读文本
    │
    └─ 构建交易提示词
        │
        ├─ 固定部分：
        │   - "Analyze the current market situation..."
        │   - "Based on the above information..."
        │
        └─ 变动部分：
            - 市场数据文本（动态）
            - additional_context（可选）
            - require_decision时的强制要求文本（可选）
    │
    ▼
AgentManager.broadcast_prompt(role="user", content=prompt)
    │
    ▼
MessageBus.publish(dialog_topic, {"role": role, "content": content})
    │
    ▼
BaseAgent.dialog_sub.recv() [订阅对话消息]
    │
    ▼
BaseAgent._handle_dialog(msg)
    │
    ├─ 追加到对话历史: self.dialog_history.append(msg)
    │
    └─ 立即触发决策: _make_decision_from_dialog(msg)
```

**Prompt发送频率：**
- 在 `run_bot.py` 第489行设置：`prompt_interval = 30` 秒
- 主循环每30秒发送一次交易提示（第502行）

### 3. Agent决策生成流程

**文件位置：** `api/agents/base_agent.py`

```
BaseAgent._generate_decision(user_prompt)
    │
    ├─ [频率限制检查]
    │   GLOBAL_DECISION_RATE_LIMITER.can_call()
    │   └─ 文件: utils/rate_limiter.py 第89行
    │   └─ 限制: 每分钟最多1次（整个bot）
    │
    ├─ [构建LLM输入消息]
    │   messages = [
    │       {"role": "system", "content": self.system_prompt},
    │       {"role": "system", "content": "Current Market Data: ..."},
    │       ...self.dialog_history[-5:],  # 最近5条对话
    │       {"role": "user", "content": user_prompt}
    │   ]
    │
    ├─ [调用LLM]
    │   self.llm.chat(messages, temperature=0.7, max_tokens=512)
    │   └─ LLM提供商: 由 llm_provider 参数决定
    │   └─ 工厂模式: api/llm_clients/factory.py
    │
    ├─ [强制第一个决策]
    │   if not self._first_decision_made:
    │       decision_text = _force_first_decision(decision_text)
    │       └─ 如果是wait/hold，强制转换为open_long
    │
    ├─ [验证JSON格式]
    │   json_valid = _validate_json_decision(decision_text)
    │
    └─ [发布决策]
        decision = {
            "agent": self.name,
            "decision": decision_text,
            "market_snapshot": self.last_market_snapshot,
            "timestamp": time.time(),
            "json_valid": json_valid,
            "allocated_capital": self.allocated_capital,
            "llm_provider": self.llm_provider
        }
        │
        ▼
        MessageBus.publish(decision_topic, decision)
```

**关键参数：**
- Temperature: `0.7`（第207行）- 让模型更愿意做出决策
- Max tokens: `512`（第207行）
- 对话历史长度: 最近5条（第200行）

### 4. 交易执行流程

**文件位置：** `api/agents/executor.py`

```
TradeExecutor.run() [独立线程]
    │
    ├─ decision_sub.recv() [订阅决策]
    │
    └─ _maybe_execute(decision_msg)
        │
        ├─ [交易频率限制]
        │   if (now - self._last_order_ts) < TRADE_INTERVAL_SECONDS:
        │       └─ 文件: config/config.py 第30行
        │       └─ 限制: 61秒（每分钟最多1次）
        │
        ├─ [解析决策]
        │   parsed = _parse_decision(decision_msg)
        │   │
        │   ├─ 方法1: _parse_json_decision() [优先]
        │   │   └─ 解析JSON格式决策
        │   │   └─ 支持: action, symbol, position_size_usd, quantity等
        │   │
        │   └─ 方法2: _parse_natural_language_decision() [回退]
        │       └─ 解析自然语言决策
        │       └─ 正则表达式匹配buy/sell等关键词
        │
        ├─ [执行交易]
        │   if self.dry_run:
        │       └─ 只打印参数，不真正下单
        │   else:
        │       └─ RoostooClient.place_order(pair, side, quantity, price)
        │           └─ 使用 API_RATE_LIMITER 限制频率
        │
        └─ [更新最后订单时间]
            self._last_order_ts = now
```

**交易频率限制：**
- 文件：`config/config.py` 第30行
- 常量：`TRADE_INTERVAL_SECONDS = 61` 秒
- 作用：确保每分钟最多执行1次交易

---

## Agent详细操作流程

### BaseAgent 核心方法

**文件位置：** `api/agents/base_agent.py`

#### 1. 初始化 (`__init__`)

```python
# 第31-70行
def __init__(self, name, bus, market_topic, dialog_topic, decision_topic, 
             system_prompt, llm_provider=None, allocated_capital=None):
    # 订阅消息总线
    self.market_sub = bus.subscribe(market_topic)      # 市场数据
    self.dialog_sub = bus.subscribe(dialog_topic)     # 对话消息
    
    # 初始化LLM客户端
    self.llm = get_llm_client(provider=llm_provider)   # 工厂模式
    
    # 初始化数据格式化器
    self.formatter = DataFormatter()
    
    # 内部状态
    self.current_tickers = {}          # 当前ticker数据
    self.current_balance = None        # 当前余额数据
    self.last_market_snapshot = None    # 最新市场快照
    self.dialog_history = []            # 对话历史
```

#### 2. 主循环 (`run`)

```python
# 第75-95行
def run(self):
    while not self._stopped:
        # 1. 接收市场数据（非阻塞）
        market_msg = self.market_sub.recv(timeout=1.0)
        if market_msg:
            self._handle_market_data(market_msg)
        
        # 2. 接收对话消息（非阻塞）
        dialog_msg = self.dialog_sub.recv(timeout=0.01)
        if dialog_msg:
            self._handle_dialog(dialog_msg)
        
        # 3. 定期自动生成决策（基于最新市场数据）
        if now - self._last_decision_ts >= self.decision_interval:
            self._maybe_make_decision()
            self._last_decision_ts = now
        
        time.sleep(0.01)  # 节流
```

#### 3. 处理市场数据 (`_handle_market_data`)

```python
# 第97-124行
def _handle_market_data(self, msg):
    data_type = msg.get("type", "unknown")
    
    if data_type == "ticker":
        pair = msg.get("pair")
        self.current_tickers[pair] = msg  # 更新ticker
    
    elif data_type == "balance":
        self.current_balance = msg  # 更新余额
    
    # 创建综合市场快照
    ticker = list(self.current_tickers.values())[0] if self.current_tickers else None
    self.last_market_snapshot = self.formatter.create_market_snapshot(
        ticker=ticker,
        balance=self.current_balance
    )
```

#### 4. 处理对话消息 (`_handle_dialog`)

```python
# 第126-139行
def _handle_dialog(self, msg):
    role = msg.get("role", "user")
    content = msg.get("content", "")
    
    # 追加到对话历史
    self.dialog_history.append({"role": role, "content": content})
    
    # 立即响应对话消息
    self._make_decision_from_dialog(msg)
```

#### 5. 生成决策 (`_generate_decision`)

```python
# 第168-236行
def _generate_decision(self, user_prompt):
    # 1. 全局决策频率限制检查
    if not GLOBAL_DECISION_RATE_LIMITER.can_call():
        return  # 跳过本次决策
    
    GLOBAL_DECISION_RATE_LIMITER.record_call()
    
    # 2. 构建LLM输入消息
    messages = [
        {"role": "system", "content": self.system_prompt},  # 系统提示词
    ]
    
    # 添加市场数据上下文
    if self.last_market_snapshot:
        market_text = self.formatter.format_for_llm(self.last_market_snapshot)
        messages.append({
            "role": "system",
            "content": f"Current Market Data:\n{market_text}"
        })
    
    # 添加最近的对话历史（控制长度）
    messages.extend(self.dialog_history[-5:])
    
    # 添加当前用户提示
    messages.append({"role": "user", "content": user_prompt})
    
    # 3. 调用LLM
    llm_out = self.llm.chat(messages, temperature=0.7, max_tokens=512)
    decision_text = llm_out.get("content") or ""
    
    # 4. 强制第一个决策必须交易
    if not self._first_decision_made:
        decision_text = self._force_first_decision(decision_text)
        self._first_decision_made = True
    
    # 5. 验证JSON格式
    json_valid = self._validate_json_decision(decision_text)
    
    # 6. 发布决策
    decision = {
        "agent": self.name,
        "decision": decision_text,
        "market_snapshot": self.last_market_snapshot,
        "timestamp": time.time(),
        "json_valid": json_valid,
        "allocated_capital": self.allocated_capital,
        "llm_provider": self.llm_provider
    }
    self.bus.publish(self.decision_topic, decision)
```

---

## Prompt系统详解

### Prompt组成结构

#### 1. 系统提示词 (System Prompt)

**文件位置：** `api/agents/prompt_manager.py` 第69-169行

**固定部分：**
```python
# 第86-95行：基础角色定义
base_prompt = f"""You are {agent_name}, an AI trading assistant for Web3 quantitative trading.

Your responsibilities:
1. Analyze real-time market data (prices, volumes, trends)
2. Monitor account balance and available funds
3. Make trading decisions based on market conditions
4. Consider risk management in all decisions

Risk Level: {risk_level}
"""
```

**变动部分：**
- `agent_name`: Agent名称（传入参数）
- `trading_strategy`: 交易策略描述（可选，第97-98行）
- `risk_level`: 风险等级（conservative/moderate/aggressive，第94行）

**风险等级配置：**
```python
# 第100-104行
risk_guidelines = {
    "conservative": "Be very cautious. Only trade when there's high confidence. Preserve capital.",
    "moderate": "Balance risk and reward. Look for good opportunities but don't take excessive risks. Make decisions when you have reasonable confidence (70%+).",
    "aggressive": "Be active in trading. Take calculated risks for higher returns. Make decisions when you have 60%+ confidence. Don't wait for perfect conditions - act on reasonable opportunities."
}
```

**信心度阈值：**
```python
# 第109行
confidence_threshold = "60%" if risk_level == "aggressive" else "70%"
```

**决策哲学部分（固定）：**
```python
# 第112-125行
decision_philosophy = f"""
IMPORTANT - Decision Making Philosophy:
- You should make trading decisions when you have reasonable confidence ({confidence_threshold} confidence is sufficient)
- For initial decisions and when market data is available, {confidence_threshold} confidence is enough to take action
- Don't always choose wait/hold - analyze the market and make decisions when opportunities exist
- Only choose wait/hold when market conditions are truly unclear or unfavorable (not just uncertain)
- Be proactive in identifying trading opportunities based on available market data
- Remember: Missing opportunities is also a risk - act when you have reasonable confidence

When making decisions, provide clear reasoning:
- What market signals you're seeing
- Why you're making this decision
- Expected outcome and risk assessment
"""
```

**JSON格式说明（固定）：**
```python
# 第128-165行
json_format_section = """
CRITICAL - Decision Format (MANDATORY JSON):
You MUST output your decision in JSON format ONLY. No exceptions.

Required JSON format:
{
  "action": "open_long | close_long | wait | hold",
  "symbol": "BTCUSDT",
  "price_ref": 100000.0,
  "position_size_usd": 1200.0,
  "stop_loss": 98700.0,
  "take_profit": 104000.0,
  "partial_close_pct": 0,
  "confidence": 88,
  "invalidation_condition": "示例：跌破 1h EMA20",
  "slippage_buffer": 0.0002,
  "reasoning": "要点：BTC 多周期一致；MACD>0；EMA20 支撑；放量 + 均线粘连突破；RR≥1:2；冷却期满足；信心 88。"
}
...
"""
```

#### 2. 交易提示词 (Trading Prompt)

**文件位置：** `api/agents/prompt_manager.py` 第171-218行

**固定部分：**
```python
# 第191-195行
prompt = f"""Analyze the current market situation and make a trading decision.

{market_text}

"""
```

**变动部分：**
1. **市场数据文本** (`market_text`)：
   - 来源：`DataFormatter.format_for_llm(market_snapshot)`
   - 文件：`api/agents/data_formatter.py` 第249-288行
   - 包含：价格、24小时涨跌幅、成交量、账户余额等

2. **额外上下文** (`additional_context`)：
   - 可选参数
   - 示例："Periodic market analysis request."

3. **强制决策要求** (`require_decision`)：
   - 当 `require_decision=True` 时添加（第200-209行）
   - 降低信心度阈值到60%
   - 要求必须做出交易决策（不能wait/hold）

**完整示例：**
```python
# 在 run_bot.py 第507-511行
trading_prompt = prompt_mgr.create_trading_prompt(
    market_snapshot=market_snapshot,
    additional_context="Periodic market analysis request.",
    require_decision=is_first_prompt  # 第一分钟内强制要求决策
)
```

#### 3. 现货交易Prompt模板

**文件位置：** `prompts/natural_language_prompt.txt`

**加载方式：**
```python
# api/agents/prompt_manager.py 第30-67行
def _load_prompt_templates(self):
    # 读取 prompts/natural_language_prompt.txt
    # 提取 agent_system_prompt_spot 变量
    # 使用正则表达式提取模板内容
```

**模板变量（占位符）：**
- `{date}`: 今日日期
- `{account_equity}`: 账户净值（USDT）
- `{available_cash}`: 可用现金（USDT）
- `{positions}`: 持仓信息
- `{price_series}`: 价格时间序列
- `{volume_series}`: 成交量时间序列
- `{recent_sharpe}`: 近期夏普比率
- `{trade_stats}`: 交易统计
- `{STOP_SIGNAL}`: 停止信号

**使用方式：**
```python
# api/agents/prompt_manager.py 第347-417行
def create_spot_prompt_from_market_data(self, market_snapshot, ...):
    # 从market_snapshot提取数据
    # 调用 get_spot_trading_prompt() 填充模板
    # 返回格式化后的prompt
```

### Prompt传递路径

```
1. PromptManager.create_trading_prompt()
   └─ 文件: api/agents/prompt_manager.py 第171行
   │
2. AgentManager.broadcast_prompt()
   └─ 文件: api/agents/manager.py 第66行
   │
3. MessageBus.publish(dialog_topic, message)
   └─ 文件: api/agents/bus.py 第24行
   │
4. BaseAgent.dialog_sub.recv()
   └─ 文件: api/agents/base_agent.py 第84行
   │
5. BaseAgent._handle_dialog()
   └─ 文件: api/agents/base_agent.py 第126行
   │
6. BaseAgent._make_decision_from_dialog()
   └─ 文件: api/agents/base_agent.py 第158行
   │
7. BaseAgent._generate_decision()
   └─ 文件: api/agents/base_agent.py 第168行
   │
8. LLM.chat(messages)
   └─ 文件: api/llm_clients/factory.py
```

---

## Rate Limit机制

### 1. API调用频率限制

**文件位置：** `utils/rate_limiter.py` 第87行

```python
API_RATE_LIMITER = RateLimiter(max_calls=5, time_window=60.0)
# 每分钟最多5次API调用
```

**使用位置：**
1. **RoostooClient** (`api/roostoo_client.py` 第91-97行)
   ```python
   if not API_RATE_LIMITER.can_call():
       wait_time = API_RATE_LIMITER.wait_time()
       if wait_time > 0:
           time.sleep(wait_time)
   API_RATE_LIMITER.record_call()
   ```

2. **MarketDataCollector** (`api/agents/market_collector.py`)
   - 间接使用：通过RoostooClient调用API时自动应用限制
   - 采集间隔：`collect_interval=12.0` 秒（确保不超过限制）

**实现原理：**
```python
# utils/rate_limiter.py 第14-83行
class RateLimiter:
    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls        # 最大调用次数
        self.time_window = time_window     # 时间窗口（秒）
        self.call_times: deque = deque()   # 调用时间记录（滑动窗口）
    
    def can_call(self) -> bool:
        # 移除时间窗口外的记录
        # 检查当前窗口内的调用次数
        return len(self.call_times) < self.max_calls
```

### 2. 决策生成频率限制

**文件位置：** `utils/rate_limiter.py` 第89行

```python
GLOBAL_DECISION_RATE_LIMITER = RateLimiter(max_calls=1, time_window=60.0)
# 整个bot每分钟最多生成1次决策
```

**使用位置：**
```python
# api/agents/base_agent.py 第177-184行
def _generate_decision(self, user_prompt: str):
    # 全局决策频率限制：整个bot每分钟最多1次
    if not GLOBAL_DECISION_RATE_LIMITER.can_call():
        wait_time = GLOBAL_DECISION_RATE_LIMITER.wait_time()
        if wait_time > 0:
            print(f"[{self.name}] ⚠️ 全局决策频率限制: 需要等待 {wait_time:.1f} 秒")
            return  # 跳过本次决策生成
    
    # 记录决策生成（全局限制）
    GLOBAL_DECISION_RATE_LIMITER.record_call()
```

**注意：**
- 这是**全局限制**，所有Agent共享同一个限制器
- 即使有多个Agent，整个系统每分钟最多生成1次决策

### 3. 交易执行频率限制

**文件位置：** `config/config.py` 第30行

```python
TRADE_INTERVAL_SECONDS = 61
# 交易执行间隔：61秒（每分钟最多1次）
```

**使用位置：**
```python
# api/agents/executor.py 第63-67行
def _maybe_execute(self, decision_msg: Dict[str, Any]):
    now = time.time()
    if self._last_order_ts is not None and (now - self._last_order_ts) < TRADE_INTERVAL_SECONDS:
        # 限频：忽略本次决策
        return
```

**与决策频率限制的区别：**
- 决策频率限制：限制Agent生成决策的频率
- 交易频率限制：限制TradeExecutor执行交易的频率
- 两者独立，但都设置为每分钟最多1次

---

## 策略强度配置

### 1. 风险等级 (Risk Level)

**配置位置：** `api/agents/prompt_manager.py` 第69-169行

**三个等级：**

1. **Conservative（保守）**
   - 信心度阈值：85%+
   - 策略：非常谨慎，只在有高信心时交易，保护资本
   - 使用场景：资金保护优先

2. **Moderate（平衡）**
   - 信心度阈值：70%+
   - 策略：平衡风险和收益，寻找好机会但不承担过度风险
   - 使用场景：默认配置

3. **Aggressive（激进）**
   - 信心度阈值：60%+
   - 策略：积极交易，为更高收益承担计算过的风险
   - 使用场景：追求更高收益

**在代码中的使用：**
```python
# run_bot.py 第300-310行
agent_1_prompt = prompt_mgr.get_system_prompt(
    agent_name="Agent1",
    trading_strategy="Actively seek trading opportunities...",
    risk_level="aggressive"  # 设置风险等级
)
```

### 2. 交易策略描述 (Trading Strategy)

**配置位置：** `run_bot.py` 第302-309行

```python
# Agent 1
trading_strategy="Actively seek trading opportunities. Make decisions when you have 60%+ confidence. Be proactive in identifying entry and exit points."

# Agent 2
trading_strategy="Actively analyze market conditions and make trading decisions when opportunities arise. Take calculated risks for better returns. 60%+ confidence is sufficient."
```

**作用：**
- 作为系统提示词的一部分传递给Agent
- 影响Agent的决策风格和行为

### 3. LLM Temperature参数

**配置位置：** `api/agents/base_agent.py` 第207行

```python
llm_out = self.llm.chat(messages, temperature=0.7, max_tokens=512)
```

**说明：**
- Temperature = 0.7：让模型更愿意做出决策（而不是总是选择wait/hold）
- 较高的temperature会增加输出的随机性和创造性

### 4. 强制第一个决策

**配置位置：** `api/agents/base_agent.py` 第238-312行

```python
def _force_first_decision(self, decision_text: str) -> str:
    # 如果第一个决策是wait/hold，强制转换为open_long
    if is_wait_hold:
        forced_decision = {
            "action": "open_long",
            "symbol": "BTCUSDT",
            "price_ref": current_price,
            "position_size_usd": 500.0,
            "confidence": 65,
            "reasoning": "First decision forced: System requires initial trading action..."
        }
        return json.dumps(forced_decision, ensure_ascii=False)
```

**目的：**
- 确保系统启动后能立即开始交易
- 避免Agent过于保守导致长时间不交易

---

## 关键文件说明

### 核心模块

| 文件 | 功能 | 关键类/函数 |
|------|------|------------|
| `run_bot.py` | 主运行脚本 | `main()` - 系统初始化和管理 |
| `api/agents/manager.py` | Agent管理器 | `AgentManager` - 管理多个Agent |
| `api/agents/base_agent.py` | Agent基类 | `BaseAgent` - 核心决策逻辑 |
| `api/agents/market_collector.py` | 市场数据采集 | `MarketDataCollector` - 定期采集数据 |
| `api/agents/executor.py` | 交易执行器 | `TradeExecutor` - 执行交易 |
| `api/agents/prompt_manager.py` | Prompt管理 | `PromptManager` - 生成和管理prompt |
| `api/agents/data_formatter.py` | 数据格式化 | `DataFormatter` - 格式化市场数据 |
| `api/agents/bus.py` | 消息总线 | `MessageBus` - 发布/订阅机制 |
| `api/agents/capital_manager.py` | 资金管理 | `CapitalManager` - 管理资金分配 |

### 配置和工具

| 文件 | 功能 | 关键配置 |
|------|------|----------|
| `config/config.py` | 配置文件 | `TRADE_INTERVAL_SECONDS = 61` |
| `utils/rate_limiter.py` | 频率限制器 | `API_RATE_LIMITER`, `GLOBAL_DECISION_RATE_LIMITER` |
| `api/roostoo_client.py` | Roostoo API客户端 | `RoostooClient` - API调用封装 |

### LLM相关

| 文件 | 功能 | 关键类 |
|------|------|--------|
| `api/llm_clients/factory.py` | LLM工厂 | `get_llm_client()` - 创建LLM客户端 |
| `api/llm_clients/base.py` | LLM基类 | `LLMClient` - 统一接口 |
| `api/llm_clients/deepseek_client.py` | DeepSeek客户端 | `DeepSeekClient` |
| `api/llm_clients/qwen_client.py` | Qwen客户端 | `QwenClient` |
| `api/llm_clients/minimax_client.py` | Minimax客户端 | `MinimaxClient` |

### Prompt模板

| 文件 | 功能 | 说明 |
|------|------|------|
| `prompts/natural_language_prompt.txt` | 现货交易模板 | 详细的加密货币现货交易prompt模板 |

---

## 总结

### 数据流总结

1. **市场数据流：**
   ```
   Roostoo API → MarketDataCollector → DataFormatter → MessageBus → BaseAgent
   ```

2. **Prompt流：**
   ```
   PromptManager → AgentManager.broadcast_prompt() → MessageBus → BaseAgent
   ```

3. **决策流：**
   ```
   BaseAgent → MessageBus → TradeExecutor → RoostooClient → Roostoo API
   ```

### 关键配置总结

| 配置项 | 值 | 位置 |
|--------|-----|------|
| API调用频率限制 | 每分钟5次 | `utils/rate_limiter.py:87` |
| 决策生成频率限制 | 每分钟1次（全局） | `utils/rate_limiter.py:89` |
| 交易执行频率限制 | 每61秒1次 | `config/config.py:30` |
| 市场数据采集间隔 | 12秒 | `run_bot.py:339` |
| Prompt发送间隔 | 30秒 | `run_bot.py:489` |
| LLM Temperature | 0.7 | `api/agents/base_agent.py:207` |
| 对话历史长度 | 最近5条 | `api/agents/base_agent.py:200` |

### Prompt组成总结

1. **系统提示词（固定+变动）：**
   - 固定：角色定义、决策哲学、JSON格式说明
   - 变动：agent_name、trading_strategy、risk_level

2. **交易提示词（固定+变动）：**
   - 固定：分析要求、决策要求
   - 变动：市场数据文本、additional_context、require_decision标志

3. **现货交易模板（从文件加载）：**
   - 位置：`prompts/natural_language_prompt.txt`
   - 包含：详细的交易规则、风险管理、策略信号等

---

**文档生成时间：** 2025-01-XX
**项目版本：** Web3DAO v1.0

