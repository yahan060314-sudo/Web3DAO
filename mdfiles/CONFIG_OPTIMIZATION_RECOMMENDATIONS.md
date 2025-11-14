# 配置优化建议清单

本文档列出所有建议优化的硬编码阈值和配置项，按照"最小改动"原则，只需将这些值改为可配置参数。

## 一、决策生成相关配置

### 1.1 BaseAgent配置

| 配置项 | 当前硬编码位置 | 当前值 | 建议配置名 | 建议默认值 | 说明 |
|--------|---------------|--------|-----------|-----------|------|
| 决策生成间隔 | `base_agent.py:39` | 60.0秒 | `DECISION_INTERVAL_SECONDS` | 60.0 | Agent定期生成决策的间隔 |
| 对话历史长度 | `base_agent.py:200` | 5条 | `DIALOG_HISTORY_LENGTH` | 5 | 保留的对话历史条数 |
| LLM Temperature | `base_agent.py:207` | 0.7 | `LLM_TEMPERATURE` | 0.7 | LLM生成决策的随机性 |
| LLM Max Tokens | `base_agent.py:207` | 512 | `LLM_MAX_TOKENS` | 512 | LLM生成的最大token数 |
| 轮询超时 | `base_agent.py:38` | 1.0秒 | `AGENT_POLL_TIMEOUT` | 1.0 | Agent轮询市场数据的超时时间 |

### 1.2 第一个决策强制配置

| 配置项 | 当前硬编码位置 | 当前值 | 建议配置名 | 建议默认值 | 说明 |
|--------|---------------|--------|-----------|-----------|------|
| 强制交易金额 | `base_agent.py:288` | 500.0 USD | `INITIAL_POSITION_SIZE_USD` | 500.0 | 第一个决策强制交易的金额 |
| 强制交易信心度 | `base_agent.py:289` | 65 | `INITIAL_DECISION_CONFIDENCE` | 65 | 强制决策的信心度 |
| 默认交易数量 | `executor.py:160` | 0.01 BTC | `DEFAULT_QUANTITY` | 0.01 | 无法获取价格时的默认数量 |

---

## 二、Prompt策略配置

### 2.1 信心度阈值配置

| 配置项 | 当前硬编码位置 | 当前值 | 建议配置名 | 建议默认值 | 说明 |
|--------|---------------|--------|-----------|-----------|------|
| Conservative信心度 | `prompt_manager.py:109` | 85% | `CONFIDENCE_THRESHOLD_CONSERVATIVE` | 85 | 保守策略的最低信心度 |
| Moderate信心度 | `prompt_manager.py:109` | 70% | `CONFIDENCE_THRESHOLD_MODERATE` | 70 | 中等策略的最低信心度 |
| Aggressive信心度 | `prompt_manager.py:109` | 60% | `CONFIDENCE_THRESHOLD_AGGRESSIVE` | 60 | 激进策略的最低信心度 |

### 2.2 决策格式验证配置

| 配置项 | 当前硬编码位置 | 当前值 | 建议配置名 | 建议默认值 | 说明 |
|--------|---------------|--------|-----------|-----------|------|
| 最小仓位大小 | 无 | 无 | `MIN_POSITION_SIZE_USD` | 100.0 | 最小交易金额（USD） |
| 最大仓位大小比例 | 无 | 无 | `MAX_POSITION_SIZE_RATIO` | 0.8 | 最大仓位占可用资金的比例 |

---

## 三、市场数据采集配置

### 3.1 采集频率配置

| 配置项 | 当前硬编码位置 | 当前值 | 建议配置名 | 建议默认值 | 说明 |
|--------|---------------|--------|-----------|-----------|------|
| 采集间隔 | `market_collector.py:29` | 12.0秒 | `MARKET_DATA_COLLECT_INTERVAL` | 12.0 | 市场数据采集间隔 |
| 价格变化阈值 | `market_collector.py:98` | 0.01 | `PRICE_CHANGE_THRESHOLD` | 0.001 | 价格变化触发阈值（建议改为0.1%） |
| 紧急波动阈值 | 无 | 无 | `EMERGENCY_VOLATILITY_THRESHOLD` | 0.03 | 紧急波动阈值（3%，5分钟内） |

### 3.2 数据发布配置

| 配置项 | 当前硬编码位置 | 当前值 | 建议配置名 | 建议默认值 | 说明 |
|--------|---------------|--------|-----------|-----------|------|
| 余额变化阈值 | `market_collector.py:119` | 0.01 | `BALANCE_CHANGE_THRESHOLD` | 0.01 | 余额变化触发阈值 |

---

## 四、交易执行配置

### 4.1 执行频率配置

| 配置项 | 当前硬编码位置 | 当前值 | 建议配置名 | 建议默认值 | 说明 |
|--------|---------------|--------|-----------|-----------|------|
| 交易执行间隔 | `config/config.py:30` | 61秒 | `TRADE_INTERVAL_SECONDS` | 61 | 交易执行的最小间隔（已有） |

### 4.2 决策解析配置

| 配置项 | 当前硬编码位置 | 当前值 | 建议配置名 | 建议默认值 | 说明 |
|--------|---------------|--------|-----------|-----------|------|
| 默认交易对 | `executor.py:21` | "BTC/USD" | `DEFAULT_TRADING_PAIR` | "BTC/USD" | 默认交易对 |

---

## 五、决策验证配置

### 5.1 数量验证配置

| 配置项 | 当前硬编码位置 | 当前值 | 建议配置名 | 建议默认值 | 说明 |
|--------|---------------|--------|-----------|-----------|------|
| 最大交易数量 | `decision_manager.py:235` | 1000 | `MAX_QUANTITY` | 1000 | 最大交易数量限制 |

### 5.2 价格验证配置

| 配置项 | 当前硬编码位置 | 当前值 | 建议配置名 | 建议默认值 | 说明 |
|--------|---------------|--------|-----------|-----------|------|
| 价格验证范围 | `decision_manager.py:245` | 0.1 (10%) | `PRICE_VALIDATION_RANGE` | 0.1 | 价格验证范围（±10%） |

### 5.3 时间验证配置

| 配置项 | 当前硬编码位置 | 当前值 | 建议配置名 | 建议默认值 | 说明 |
|--------|---------------|--------|-----------|-----------|------|
| 决策超时时间 | `decision_manager.py:27` | 5.0秒 | `DECISION_TIMEOUT` | 5.0 | 决策有效期（超时后不执行） |
| 决策综合时间窗口 | `decision_manager.py:46` | 2.0秒 | `CONSENSUS_WINDOW` | 2.0 | 多AI决策综合的时间窗口 |

---

## 六、资金管理配置

### 6.1 初始资金配置

| 配置项 | 当前硬编码位置 | 当前值 | 建议配置名 | 建议默认值 | 说明 |
|--------|---------------|--------|-----------|-----------|------|
| 初始资金 | `capital_manager.py:43` | 50000.0 USD | `INITIAL_CAPITAL` | 50000.0 | 初始资金（已有，但可改进） |

### 6.2 资金预留配置

| 配置项 | 当前硬编码位置 | 当前值 | 建议配置名 | 建议默认值 | 说明 |
|--------|---------------|--------|-----------|-----------|------|
| 资金预留比例 | 无 | 100% | `CAPITAL_RESERVE_RATIO` | 1.1 | 资金预留比例（110%应对滑点） |

### 6.3 资金分配配置

| 配置项 | 当前硬编码位置 | 当前值 | 建议配置名 | 建议默认值 | 说明 |
|--------|---------------|--------|-----------|-----------|------|
| 资金分配权重 | 无 | 平均分配 | `CAPITAL_ALLOCATION_WEIGHTS` | `{"agent_1": 0.5, "agent_2": 0.5}` | Agent资金分配权重（JSON格式） |

---

## 七、风险控制配置

### 7.1 止损止盈配置

| 配置项 | 当前硬编码位置 | 当前值 | 建议配置名 | 建议默认值 | 说明 |
|--------|---------------|--------|-----------|-----------|------|
| 最小止损距离 | 无 | 无 | `MIN_STOP_LOSS_DISTANCE` | 0.01 | 最小止损距离（1%） |
| 最小盈亏比 | 无 | 无 | `MIN_RISK_REWARD_RATIO` | 2.0 | 最小盈亏比（2:1） |

### 7.2 仓位管理配置

| 配置项 | 当前硬编码位置 | 当前值 | 建议配置名 | 建议默认值 | 说明 |
|--------|---------------|--------|-----------|-----------|------|
| 单笔风险比例 | 无 | 无 | `MAX_SINGLE_TRADE_RISK` | 0.02 | 单笔交易最大风险（账户净值的2%） |
| 单一币种集中度 | 无 | 无 | `MAX_SINGLE_CURRENCY_CONCENTRATION` | 0.4 | 单一币种最大持仓比例（40%） |

---

## 八、频率限制配置

### 8.1 API调用限制

| 配置项 | 当前硬编码位置 | 当前值 | 建议配置名 | 建议默认值 | 说明 |
|--------|---------------|--------|-----------|-----------|------|
| API调用频率限制 | `rate_limiter.py:87` | 5次/分钟 | `API_RATE_LIMIT_MAX_CALLS` | 5 | API调用频率限制（次数） |
| API调用时间窗口 | `rate_limiter.py:87` | 60秒 | `API_RATE_LIMIT_TIME_WINDOW` | 60 | API调用频率限制（时间窗口） |

### 8.2 决策频率限制

| 配置项 | 当前硬编码位置 | 当前值 | 建议配置名 | 建议默认值 | 说明 |
|--------|---------------|--------|-----------|-----------|------|
| 全局决策频率限制 | `rate_limiter.py:89` | 1次/分钟 | `GLOBAL_DECISION_RATE_LIMIT` | 1 | 全局决策频率限制（次数） |
| 全局决策时间窗口 | `rate_limiter.py:89` | 60秒 | `GLOBAL_DECISION_TIME_WINDOW` | 60 | 全局决策频率限制（时间窗口） |

---

## 九、实施建议

### 9.1 优先级分类

**高优先级（立即实施）**：
1. 决策生成间隔（`DECISION_INTERVAL_SECONDS`）
2. 价格变化阈值（`PRICE_CHANGE_THRESHOLD`）- 改为百分比
3. 资金预留比例（`CAPITAL_RESERVE_RATIO`）
4. 最大仓位比例（`MAX_POSITION_SIZE_RATIO`）

**中优先级（近期实施）**：
1. 信心度阈值配置（`CONFIDENCE_THRESHOLD_*`）
2. LLM参数配置（`LLM_TEMPERATURE`, `LLM_MAX_TOKENS`）
3. 决策验证配置（`MAX_QUANTITY`, `PRICE_VALIDATION_RANGE`）

**低优先级（长期优化）**：
1. 资金分配权重（`CAPITAL_ALLOCATION_WEIGHTS`）
2. 止损止盈配置（`MIN_STOP_LOSS_DISTANCE`, `MIN_RISK_REWARD_RATIO`）
3. 仓位管理配置（`MAX_SINGLE_TRADE_RISK`, `MAX_SINGLE_CURRENCY_CONCENTRATION`）

### 9.2 实施步骤

1. **第一步**：在`config/config.py`中添加所有配置常量
2. **第二步**：在代码中使用配置常量替代硬编码值
3. **第三步**：在`.env.example`文件中添加所有配置项的说明
4. **第四步**：更新文档，说明每个配置项的含义和建议值

### 9.3 配置示例

在`config/config.py`中添加：

```python
# 决策生成配置
DECISION_INTERVAL_SECONDS = float(os.getenv("DECISION_INTERVAL_SECONDS", "60.0"))
DIALOG_HISTORY_LENGTH = int(os.getenv("DIALOG_HISTORY_LENGTH", "5"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "512"))

# 信心度阈值配置
CONFIDENCE_THRESHOLD_CONSERVATIVE = int(os.getenv("CONFIDENCE_THRESHOLD_CONSERVATIVE", "85"))
CONFIDENCE_THRESHOLD_MODERATE = int(os.getenv("CONFIDENCE_THRESHOLD_MODERATE", "70"))
CONFIDENCE_THRESHOLD_AGGRESSIVE = int(os.getenv("CONFIDENCE_THRESHOLD_AGGRESSIVE", "60"))

# 市场数据配置
MARKET_DATA_COLLECT_INTERVAL = float(os.getenv("MARKET_DATA_COLLECT_INTERVAL", "12.0"))
PRICE_CHANGE_THRESHOLD = float(os.getenv("PRICE_CHANGE_THRESHOLD", "0.001"))  # 0.1%
EMERGENCY_VOLATILITY_THRESHOLD = float(os.getenv("EMERGENCY_VOLATILITY_THRESHOLD", "0.03"))  # 3%

# 交易执行配置
MAX_QUANTITY = float(os.getenv("MAX_QUANTITY", "1000"))
PRICE_VALIDATION_RANGE = float(os.getenv("PRICE_VALIDATION_RANGE", "0.1"))  # 10%
DECISION_TIMEOUT = float(os.getenv("DECISION_TIMEOUT", "5.0"))

# 资金管理配置
CAPITAL_RESERVE_RATIO = float(os.getenv("CAPITAL_RESERVE_RATIO", "1.1"))  # 110%
MAX_POSITION_SIZE_RATIO = float(os.getenv("MAX_POSITION_SIZE_RATIO", "0.8"))  # 80%
INITIAL_POSITION_SIZE_USD = float(os.getenv("INITIAL_POSITION_SIZE_USD", "500.0"))
```

在`.env.example`中添加：

```bash
# 决策生成配置
DECISION_INTERVAL_SECONDS=60.0
DIALOG_HISTORY_LENGTH=5
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=512

# 信心度阈值配置
CONFIDENCE_THRESHOLD_CONSERVATIVE=85
CONFIDENCE_THRESHOLD_MODERATE=70
CONFIDENCE_THRESHOLD_AGGRESSIVE=60

# 市场数据配置
MARKET_DATA_COLLECT_INTERVAL=12.0
PRICE_CHANGE_THRESHOLD=0.001  # 0.1%
EMERGENCY_VOLATILITY_THRESHOLD=0.03  # 3%

# 交易执行配置
MAX_QUANTITY=1000
PRICE_VALIDATION_RANGE=0.1  # 10%
DECISION_TIMEOUT=5.0

# 资金管理配置
CAPITAL_RESERVE_RATIO=1.1  # 110%
MAX_POSITION_SIZE_RATIO=0.8  # 80%
INITIAL_POSITION_SIZE_USD=500.0
```

---

## 十、总结

本文档列出了**30+个**可以优化的硬编码阈值和配置项。按照"最小改动"原则，只需要：

1. 在`config/config.py`中添加配置常量
2. 在代码中使用配置常量替代硬编码值
3. 在`.env`文件中提供默认值

**预计改动量**：
- 新增配置常量：约30行代码
- 修改硬编码值：约20处
- 总改动量：<100行代码

**预期收益**：
- 提高系统灵活性
- 便于不同市场条件下的调优
- 降低维护成本
- 提高系统可测试性

