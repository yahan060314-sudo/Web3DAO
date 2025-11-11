# 决策解析问题分析

## 当前问题

### 1. Prompt格式不一致
- **`get_system_prompt()`**: 要求自然语言格式 `"buy [quantity] [pair]"`
- **`natural_language_prompt.txt`**: 要求JSON格式输出
- **结果**: Agent可能输出JSON，但executor只支持自然语言解析

### 2. 自然语言解析的脆弱性

#### 问题1: 同时出现buy和sell
```python
# 当前代码 (executor.py 81-84行)
if "buy" in text:
    side = "BUY"
elif "sell" in text:
    side = "SELL"
```

**问题场景**:
- Agent输出: "I was asked to choose between buy or sell, and I decide to buy 0.01 BTC"
- 解析结果: ✅ 正确识别为BUY（因为先匹配buy）
- Agent输出: "I was asked to choose between sell or buy, and I decide to sell 0.01 BTC"  
- 解析结果: ❌ 错误识别为BUY（因为先匹配buy）

#### 问题2: 数字提取不准确
```python
# 当前代码 (executor.py 89行)
qty_match = re.search(r"(\d+\.?\d*)", text)
quantity = float(qty_match.group(1)) if qty_match else 0.01
```

**问题场景**:
- Agent输出: "buy 0.01 BTC at 100000"
- 解析结果: ✅ 正确提取0.01
- Agent输出: "Based on analysis, I recommend buying 0.01 BTC. The current price is 100000."
- 解析结果: ✅ 正确提取0.01（第一个数字）
- Agent输出: "The price is 100000, I want to buy 0.01 BTC"
- 解析结果: ❌ 错误提取100000（第一个数字是价格）

#### 问题3: 没有格式验证
- 如果Agent输出"hold"或"wait"，当前代码会返回None（因为找不到buy/sell）
- 但如果Agent说"I decide to hold"，可能被误解析

### 3. JSON格式的必要性分析

**结论: JSON格式是必要的**

**原因**:
1. `natural_language_prompt.txt` 已经要求JSON格式输出
2. JSON格式更可靠，避免自然语言歧义
3. JSON包含更多信息（stop_loss, take_profit, confidence等）
4. 结构化数据更容易验证和调试

**当前状态**:
- ✅ `natural_language_prompt.txt` 要求JSON格式
- ❌ `executor.py` 不支持JSON解析
- ❌ `get_system_prompt()` 要求自然语言格式

## 解决方案

### 方案1: 支持JSON格式（推荐）
- 优先解析JSON格式
- 如果JSON解析失败，回退到自然语言解析
- 这样既支持组友的prompt模板，也兼容旧的格式

### 方案2: 统一为自然语言格式
- 修改`natural_language_prompt.txt`要求自然语言格式
- 改进自然语言解析的健壮性
- 缺点：丢失结构化信息（stop_loss, take_profit等）

### 方案3: 统一为JSON格式
- 修改`get_system_prompt()`要求JSON格式
- 完全移除自然语言解析
- 缺点：不兼容旧的prompt

**推荐方案1**: 同时支持JSON和自然语言，优先JSON

