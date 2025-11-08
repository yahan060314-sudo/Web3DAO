# JSON格式强制要求实现总结

## 问题回答

### 1. JSON格式是否更有利于结果提取？

**答案：是的**

**优势**:
- ✅ **结构化数据**：易于解析，避免自然语言歧义
- ✅ **信息完整**：包含stop_loss, take_profit, confidence等完整信息
- ✅ **易于验证**：可以验证必需字段是否存在
- ✅ **类型安全**：数值类型明确，避免字符串解析错误
- ✅ **扩展性强**：可以轻松添加新字段而不影响解析

### 2. 当前实现是否给了AI选择？

**改进前**：是的，给了两种选择（JSON或自然语言）

**改进后**：**已强制要求JSON格式**

### 3. natural_language_prompt.txt的导入方式

**回答**：**不是复制，而是动态加载**

**实现方式**：
1. `PromptManager._load_prompt_templates()` 方法在初始化时读取文件
2. 使用正则表达式提取 `agent_system_prompt_spot = dedent("""...""")` 中的内容
3. 提取的模板存储在 `self.spot_trading_template` 中
4. 通过 `create_spot_prompt_from_market_data()` 方法使用模板

**优点**：
- ✅ 保持文件独立性，便于组友维护
- ✅ 修改 `natural_language_prompt.txt` 后无需修改代码
- ✅ 模板内容完整保留（包括所有规则、格式要求等）

**检查结果**：
- ✅ 模板加载逻辑完整
- ✅ 所有占位符（{date}, {account_equity}, {available_cash}, {positions}, {price_series}, {volume_series}, {recent_sharpe}, {trade_stats}, {STOP_SIGNAL}）都已正确处理
- ✅ JSON格式要求已在模板中明确（"仅接受下述 JSON"）

## 实现改进

### 1. 强制JSON格式要求

**修改位置**：`api/agents/prompt_manager.py` 的 `get_system_prompt()` 方法

**改进内容**：
- ❌ 移除了自然语言格式选项
- ✅ 强制要求JSON格式输出
- ✅ 提供详细的JSON格式示例
- ✅ 明确说明不符合格式的后果

### 2. JSON格式验证

**新增位置**：`api/agents/base_agent.py` 的 `_validate_json_decision()` 方法

**功能**：
- ✅ 验证决策文本是否包含有效的JSON
- ✅ 检查必需字段（action）是否存在
- ✅ 在决策消息中标记 `json_valid` 字段

### 3. 特殊情况处理

**实现位置**：`api/agents/executor.py` 的 `_maybe_execute()` 方法

**处理方案**：
1. **JSON格式验证失败**：
   - 标记为 `json_valid=False`
   - 打印警告信息
   - **拒绝执行交易**（REJECTED）
   - 预留回退逻辑接口（注释说明可以使用其他Agent的决策）

2. **解析失败但可能是wait/hold**：
   - 如果JSON格式有效但action是wait/hold，正常处理（不执行交易）
   - 如果JSON格式无效，拒绝执行

3. **回退机制**（预留，未实现）：
   ```python
   # 这里可以添加回退逻辑（如使用其他Agent的决策）
   # 但根据用户要求，AI分工还没实现，暂时不添加
   ```

## 使用方式

### 使用natural_language_prompt.txt（推荐）

```python
pm = PromptManager()
spot_prompt = pm.create_spot_prompt_from_market_data(snapshot)
# Agent会输出JSON格式，executor会自动解析
```

### 使用默认system prompt（也要求JSON）

```python
pm = PromptManager()
system_prompt = pm.get_system_prompt("Agent1")
# Agent也会被要求输出JSON格式
```

## JSON格式要求

### 必需字段

```json
{
  "action": "open_long | close_long | wait | hold",
  "reasoning": "决策理由（必需）"
}
```

### 完整字段（open_long/close_long时）

```json
{
  "action": "open_long",
  "symbol": "BTCUSDT",
  "price_ref": 100000.0,
  "position_size_usd": 1200.0,
  "stop_loss": 98700.0,
  "take_profit": 104000.0,
  "partial_close_pct": 0,
  "confidence": 88,
  "invalidation_condition": "失效条件",
  "slippage_buffer": 0.0002,
  "reasoning": "决策理由"
}
```

### wait/hold时的简化格式

```json
{
  "action": "wait",
  "reasoning": "Market conditions not favorable"
}
```

## 验证流程

1. **Agent生成决策** → `BaseAgent._generate_decision()`
2. **JSON格式验证** → `BaseAgent._validate_json_decision()`
3. **标记验证结果** → `decision["json_valid"] = True/False`
4. **Executor接收决策** → `TradeExecutor._maybe_execute()`
5. **检查验证结果**：
   - 如果 `json_valid=False` → **拒绝执行**，打印警告
   - 如果 `json_valid=True` → 尝试解析JSON
   - 如果解析失败但可能是wait/hold → 正常处理

## 特殊情况处理

### 情况1：Agent输出非JSON格式

**处理**：
- ✅ 标记 `json_valid=False`
- ✅ 打印警告信息
- ✅ **拒绝执行交易**
- ⚠️ 预留回退接口（待AI分工实现后使用）

### 情况2：Agent输出JSON但格式错误

**处理**：
- ✅ 尝试解析，如果失败则标记 `json_valid=False`
- ✅ 拒绝执行交易

### 情况3：Agent输出JSON但缺少必需字段

**处理**：
- ✅ 如果缺少 `action` 字段，标记 `json_valid=False`
- ✅ 拒绝执行交易

### 情况4：Agent输出JSON但action是wait/hold

**处理**：
- ✅ 正常处理，不执行交易（这是预期的行为）

## 总结

✅ **JSON格式已强制要求**：所有Agent必须输出JSON格式

✅ **验证机制已实现**：自动验证JSON格式有效性

✅ **特殊情况已处理**：非JSON格式会被拒绝，预留回退接口

✅ **natural_language_prompt.txt动态加载**：不是复制，而是运行时读取，保持文件独立性

✅ **模板内容完整**：所有占位符和规则都已正确处理

