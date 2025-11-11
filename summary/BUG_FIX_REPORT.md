# Bug修复报告 - Agent未接收到数据问题

## 问题分析

### 现象
从测试日志可以看到：
1. ✅ Roostoo API连接成功，数据可以获取
2. ✅ DataFormatter可以格式化数据
3. ❌ Agent显示没有接收到数据：`I cannot make a trading recommendation at this time because the market data for BTC/USD is missing.`
4. ❌ MarketDataCollector显示：`Published ticker for BTC/USD: $N/A`

### 根本原因

**问题1: DataFormatter无法正确解析Roostoo返回的数据格式**

Roostoo API返回的实际格式：
```python
{
    'Success': True,
    'ErrMsg': '',
    'ServerTime': 1762565986151,
    'Data': {  # 注意：大写的Data
        'BTC/USD': {  # 交易对作为key
            'MaxBid': 103149.87,
            'MinAsk': 103149.88,
            'LastPrice': 103149.88,  # 注意：LastPrice（大写L）
            'Change': 0.0189,  # 小数形式，表示1.89%
            'CoinTradeValue': 31670.99277,
            'UnitTradeValue': 3213826873.114794
        }
    }
}
```

但DataFormatter期望的格式是：
```python
{
    'data': {  # 小写的data
        'price': '45000.0',  # 直接有price字段
        'volume24h': '1234567.89',
        ...
    }
}
```

**问题2: Balance数据格式不匹配**

Roostoo返回的balance格式：
```python
{
    'Success': True,
    'SpotWallet': {
        'USD': {'Free': 50000, 'Lock': 0}
    },
    'MarginWallet': {}
}
```

但DataFormatter期望的格式是：
```python
{
    'data': {
        'totalBalance': 10000.0,
        'balances': [...]
    }
}
```

**问题3: Prompt模板格式化错误**

组友的模板中包含JSON示例，使用花括号`{}`，导致Python的`format()`方法误解析：
```
[PromptManager] Error formatting spot trading prompt: missing key '\n  "action"'
```

## 修复方案

### 修复1: DataFormatter.format_ticker()

**文件**: `api/agents/data_formatter.py`

**改动**:
1. ✅ 处理Roostoo的嵌套结构：`Data['BTC/USD']`
2. ✅ 支持大写的`Data`键
3. ✅ 正确提取`LastPrice`（而不是`lastPrice`）
4. ✅ 处理`Change`字段（小数形式转换为百分比）
5. ✅ 使用`MaxBid`和`MinAsk`计算high/low

**关键代码**:
```python
# 处理嵌套结构：data = {'BTC/USD': {...}}
if pair and pair in data:
    pair_data = data[pair]  # 提取交易对数据
    formatted["pair"] = pair
elif len(data) == 1 and isinstance(list(data.values())[0], dict):
    # 自动检测交易对
    pair_key = list(data.keys())[0]
    pair_data = data[pair_key]

# 提取价格（Roostoo使用LastPrice）
if "LastPrice" in pair_data:
    formatted["price"] = float(pair_data["LastPrice"])
```

### 修复2: DataFormatter.format_balance()

**文件**: `api/agents/data_formatter.py`

**改动**:
1. ✅ 处理Roostoo的`SpotWallet`格式
2. ✅ 正确提取`Free`和`Lock`字段
3. ✅ 计算总余额和可用余额

**关键代码**:
```python
# 处理Roostoo的SpotWallet格式
spot_wallet = data.get("SpotWallet", {})
if spot_wallet:
    for currency, wallet_info in spot_wallet.items():
        free = float(wallet_info.get("Free", 0))
        locked = float(wallet_info.get("Lock", 0))
        total = free + locked
        # ...
```

### 修复3: PromptManager.get_spot_trading_prompt()

**文件**: `api/agents/prompt_manager.py`

**改动**:
1. ✅ 使用字符串替换而不是`format()`方法
2. ✅ 避免JSON示例中的花括号被误解析

**关键代码**:
```python
# 使用简单的字符串替换（避免JSON示例中的花括号被format()误解析）
result = self.spot_trading_template
result = result.replace('{date}', date)
result = result.replace('{account_equity}', account_equity)
# ... 其他占位符
```

## 测试验证

### 修复前的问题
```
[MarketDataCollector] Published ticker for BTC/USD: $N/A
[test_agent] Published decision: I cannot make a trading recommendation... market data is missing.
```

### 修复后的预期
```
[MarketDataCollector] Published ticker for BTC/USD: $103149.88
[test_agent] Published decision: Based on current market analysis...
```

## 数据格式对照表

| 字段 | Roostoo格式 | DataFormatter提取 | 格式化后 |
|------|------------|---------------|----------|
| 价格 | `LastPrice` | ✅ `LastPrice` | `price: 103149.88` |
| 涨跌幅 | `Change: 0.0189` | ✅ `Change` (转换为%) | `change_24h: 1.89` |
| 成交量 | `UnitTradeValue` | ✅ `UnitTradeValue` | `volume_24h: 3213826873.11` |
| 最高价 | `MaxBid, MinAsk` | ✅ `max(MaxBid, MinAsk)` | `high_24h: 103149.88` |
| 余额 | `SpotWallet.USD.Free` | ✅ `SpotWallet` | `available_balance: 50000.0` |

## 验证步骤

运行修复后的测试：
```bash
python test_complete_system.py
```

应该看到：
- ✅ Ticker数据正确提取价格
- ✅ Balance数据正确提取余额
- ✅ Agent可以接收到完整的数据
- ✅ Agent可以生成基于数据的决策

