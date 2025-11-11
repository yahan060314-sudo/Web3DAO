# API 功能对比：Roostoo vs DeepSeek/Qwen

## 🎯 核心区别

### Roostoo API = 交易执行平台（手）
### DeepSeek/Qwen = AI决策大脑（脑）

它们的作用完全不同，但在交易系统中缺一不可。

---

## 📊 功能对比表

| 特性 | Roostoo API | DeepSeek/Qwen API |
|------|------------|------------------|
| **作用** | 执行交易操作 | 生成交易决策 |
| **类比** | 股票交易所 | AI分析师 |
| **功能** | 买入/卖出、获取市场数据、查询账户 | 分析市场、做出买卖决策 |
| **输入** | 交易指令（买入/卖出、数量、价格） | 市场数据、交易历史 |
| **输出** | 交易结果（订单ID、成交价格） | 交易决策（买入/卖出建议） |
| **角色** | 执行者 | 决策者 |
| **位置** | 交易系统的最后一步 | 交易系统的第一步 |

---

## 🔄 完整流程

```
┌─────────────────────────────────────────────────────────────┐
│ 步骤1: 获取市场数据 (Roostoo API)                            │
│                                                              │
│  Roostoo API:                                                │
│    - 获取BTC价格: $50,000                                    │
│    - 获取账户余额: $10,000                                   │
│    - 获取交易历史                                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 步骤2: AI分析市场 (DeepSeek/Qwen API)                        │
│                                                              │
│  DeepSeek/Qwen API:                                          │
│    - 输入: 市场数据、交易历史                                │
│    - 分析: "当前BTC价格$50,000，趋势向上，建议买入"         │
│    - 输出: 交易决策 "买入 0.01 BTC"                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 步骤3: 执行交易 (Roostoo API)                                │
│                                                              │
│  Roostoo API:                                                │
│    - 接收指令: "买入 0.01 BTC"                               │
│    - 执行交易: 在交易所买入 0.01 BTC                         │
│    - 返回结果: 订单ID: 12345, 成交价格: $50,000             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 详细功能说明

### Roostoo API 功能

#### 1. 获取市场数据
```python
# 获取BTC价格
ticker = client.get_ticker(pair="BTC/USD")
# 返回: {"price": 50000.0, "volume": 1000000, ...}
```

#### 2. 获取账户信息
```python
# 获取账户余额
balance = client.get_balance()
# 返回: {"total": 10000.0, "available": 8000.0, ...}
```

#### 3. 执行交易
```python
# 买入BTC
result = client.place_order(
    pair="BTC/USD",
    side="BUY",
    quantity=0.01
)
# 返回: {"order_id": "12345", "status": "filled", ...}
```

#### 4. 查询订单
```python
# 查询订单状态
order = client.query_order(order_id="12345")
# 返回: {"status": "filled", "price": 50000.0, ...}
```

#### 5. 取消订单
```python
# 取消订单
client.cancel_order(order_id="12345")
```

**总结**: Roostoo API 是**交易执行平台**，负责：
- ✅ 获取市场数据
- ✅ 执行买卖操作
- ✅ 管理账户
- ✅ 查询订单

---

### DeepSeek/Qwen API 功能

#### 1. 分析市场
```python
# 输入: 市场数据
messages = [
    {"role": "system", "content": "You are a trading analyst."},
    {"role": "user", "content": "BTC price is $50,000. Should I buy or sell?"}
]

# AI分析并生成决策
response = client.chat(messages)
# 返回: "Based on current market conditions, I recommend buying 0.01 BTC"
```

#### 2. 生成交易决策
```python
# AI分析市场数据，生成交易决策
decision = client.chat(messages)
# 返回: {"action": "buy", "quantity": 0.01, "reasoning": "..."}
```

#### 3. 风险评估
```python
# AI评估交易风险
risk_assessment = client.chat(messages)
# 返回: "Risk level: Medium. Recommended position size: 0.01 BTC"
```

**总结**: DeepSeek/Qwen API 是**AI决策大脑**，负责：
- ✅ 分析市场数据
- ✅ 生成交易决策
- ✅ 评估风险
- ✅ 提供交易建议

---

## 💡 类比说明

### 股票交易类比

**Roostoo API** = **股票交易所**（如纽约证券交易所）
- 提供交易平台
- 执行买卖操作
- 管理账户
- 提供市场数据

**DeepSeek/Qwen API** = **股票分析师**
- 分析市场趋势
- 做出买卖建议
- 评估投资风险
- 提供交易策略

### 完整交易流程类比

```
1. 交易所（Roostoo）提供市场数据 → "BTC价格: $50,000"
   ↓
2. 分析师（AI）分析数据 → "建议买入"
   ↓
3. 交易所（Roostoo）执行交易 → "已买入 0.01 BTC"
   ↓
4. 交易所（Roostoo）返回结果 → "订单ID: 12345"
```

---

## 🔗 它们如何协作

### 在你的交易系统中

```python
# 1. 使用 Roostoo API 获取市场数据
from api.roostoo_client import RoostooClient
roostoo = RoostooClient()
ticker = roostoo.get_ticker("BTC/USD")  # 获取价格
balance = roostoo.get_balance()  # 获取余额

# 2. 使用 DeepSeek/Qwen API 分析数据并生成决策
from api.llm_clients import get_llm_client
llm = get_llm_client()  # DeepSeek 或 Qwen

messages = [
    {"role": "system", "content": "You are a trading analyst."},
    {"role": "user", "content": f"BTC price: ${ticker['price']}. Balance: ${balance['total']}. What should I do?"}
]

decision = llm.chat(messages)  # AI生成决策: "buy 0.01 BTC"

# 3. 使用 Roostoo API 执行交易
parsed_decision = parse_decision(decision)  # 解析决策
result = roostoo.place_order(
    pair="BTC/USD",
    side=parsed_decision["side"],  # "BUY"
    quantity=parsed_decision["quantity"]  # 0.01
)  # 执行交易
```

---

## 📋 功能对比总结

### Roostoo API
- ✅ **交易执行平台**
- ✅ **获取市场数据**
- ✅ **执行买卖操作**
- ✅ **管理账户**
- ✅ **查询订单**

### DeepSeek/Qwen API
- ✅ **AI决策大脑**
- ✅ **分析市场数据**
- ✅ **生成交易决策**
- ✅ **评估风险**
- ✅ **提供交易建议**

---

## 🎯 关键区别

### 1. 作用不同

**Roostoo API**:
- 执行交易操作
- 类似于"手"（执行者）

**DeepSeek/Qwen API**:
- 生成交易决策
- 类似于"脑"（决策者）

### 2. 输入输出不同

**Roostoo API**:
- 输入: 交易指令（买入/卖出、数量、价格）
- 输出: 交易结果（订单ID、成交价格）

**DeepSeek/Qwen API**:
- 输入: 市场数据、交易历史
- 输出: 交易决策（买入/卖出建议）

### 3. 角色不同

**Roostoo API**:
- 交易执行平台
- 类似于股票交易所

**DeepSeek/Qwen API**:
- AI分析师
- 类似于股票分析师

---

## 🔄 完整交易系统流程

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 数据采集 (Roostoo API)                                    │
│    - 获取市场数据（价格、成交量）                            │
│    - 获取账户余额                                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. 数据格式化                                                │
│    - 将市场数据格式化为AI可理解的格式                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. AI分析 (DeepSeek/Qwen API)                                │
│    - 分析市场数据                                            │
│    - 生成交易决策                                            │
│    - 输出: "买入 0.01 BTC"                                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. 决策解析                                                  │
│    - 解析AI的决策文本                                        │
│    - 提取交易参数（买入/卖出、数量、价格）                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. 执行交易 (Roostoo API)                                    │
│    - 调用 place_order() 下单                                 │
│    - 返回交易结果                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 💻 代码示例

### 完整交易系统示例

```python
# 1. 初始化客户端
from api.roostoo_client import RoostooClient
from api.llm_clients import get_llm_client

roostoo = RoostooClient()  # Roostoo API (交易平台)
llm = get_llm_client()  # DeepSeek/Qwen API (AI大脑)

# 2. 获取市场数据 (Roostoo API)
ticker = roostoo.get_ticker("BTC/USD")
balance = roostoo.get_balance()

# 3. AI分析并生成决策 (DeepSeek/Qwen API)
messages = [
    {"role": "system", "content": "You are a trading analyst."},
    {"role": "user", "content": f"BTC price: ${ticker['price']}. Balance: ${balance['total']}. What should I do?"}
]
decision = llm.chat(messages)  # AI生成决策

# 4. 解析决策
parsed = parse_decision(decision)  # 解析: {"side": "BUY", "quantity": 0.01}

# 5. 执行交易 (Roostoo API)
result = roostoo.place_order(
    pair="BTC/USD",
    side=parsed["side"],
    quantity=parsed["quantity"]
)  # 执行交易

print(f"交易完成: {result}")
```

---

## 🎯 总结

### Roostoo API ≠ DeepSeek/Qwen API

它们的作用完全不同：

1. **Roostoo API** = **交易执行平台**
   - 执行买卖操作
   - 获取市场数据
   - 管理账户

2. **DeepSeek/Qwen API** = **AI决策大脑**
   - 分析市场数据
   - 生成交易决策
   - 提供交易建议

### 它们如何协作

1. **Roostoo API** 提供市场数据
2. **DeepSeek/Qwen API** 分析数据并生成决策
3. **Roostoo API** 执行交易

### 在你的系统中

- **Roostoo API**: 负责交易执行（`api/roostoo_client.py`）
- **DeepSeek/Qwen API**: 负责决策生成（`api/llm_clients/`）
- **TradeExecutor**: 负责连接两者（`api/agents/executor.py`）

---

## 📚 相关文档

- [HOW_DECISION_TO_MARKET_WORKS.md](./HOW_DECISION_TO_MARKET_WORKS.md) - 决策到市场的完整流程
- [api/roostoo_client.py](./api/roostoo_client.py) - Roostoo API 客户端
- [api/llm_clients/](./api/llm_clients/) - LLM 客户端（DeepSeek/Qwen）

