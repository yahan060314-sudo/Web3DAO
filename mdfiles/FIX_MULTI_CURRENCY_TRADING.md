# 修复：Agent只买比特币的问题

## 问题描述
Agent一直在买比特币，不买其他币种。

## 根本原因
1. **MarketDataCollector默认只采集BTC/USD**：默认配置只采集BTC/USD的交易数据
2. **BaseAgent只使用第一个ticker**：创建market snapshot时只使用了第一个ticker数据
3. **Prompt偏向BTC**：Prompt中主要使用BTC作为示例，没有明确鼓励多币种交易
4. **缺少交易所信息**：系统没有定期获取和发布所有可用交易对的信息

## 解决方案

### 1. MarketDataCollector - 自动发现所有交易对
- 添加 `auto_discover_pairs` 参数（默认True）
- 自动从Roostoo API获取所有可用交易对
- 定期采集交易所信息（exchange_info）并发布到消息总线
- 自动更新交易对列表

**修改文件**: `api/agents/market_collector.py`

**关键变更**:
- 添加 `_discover_available_pairs()` 方法：自动获取所有可用交易对
- 添加 `_collect_exchange_info()` 方法：定期采集交易所信息
- 修改 `get_latest_snapshot()`：传递所有ticker数据（字典格式）

### 2. BaseAgent - 支持多ticker数据
- 修改 `_handle_market_data()`：处理exchange_info消息
- 修改market snapshot创建：使用所有ticker数据（字典格式），而不是只使用第一个
- 添加 `current_exchange_info` 属性：存储交易所信息

**修改文件**: `api/agents/base_agent.py`

**关键变更**:
- 添加 `current_exchange_info` 属性
- 修改market snapshot创建逻辑：使用 `tickers` 字典而不是单个 `ticker`

### 3. DataFormatter - 支持多ticker格式
- 修改 `create_market_snapshot()`：支持传入多个ticker数据（字典格式）
- 保持向后兼容：仍然支持单个ticker参数

**修改文件**: `api/agents/data_formatter.py`

**关键变更**:
- 添加 `tickers` 参数（字典格式）
- 如果提供了 `tickers`，使用它；否则使用单个 `ticker`（向后兼容）
- snapshot同时包含 `tickers` 字典和 `ticker` 单个值（向后兼容）

### 4. Prompt - 明确鼓励多币种交易
- 在基本规则中添加"多币种交易策略"部分
- 明确说明：系统会提供所有可用交易对数据
- 鼓励分析ETH、SOL、BNB等其他主流币种
- 要求根据技术指标选择最优币种

**修改文件**: `prompts/natural_language_prompt.txt`

**关键变更**:
- 添加"重要：多币种交易策略"部分
- 明确要求不要只关注BTC
- 要求比较所有可用币种，选择最有潜力的

### 5. 示例脚本更新
- 更新 `dual_ai_example.py`：使用自动发现所有交易对

**修改文件**: `api/agents/dual_ai_example.py`

**关键变更**:
- 设置 `pairs=None`（自动发现）
- 设置 `auto_discover_pairs=True`
- 调整 `collect_interval=12.0`（避免API限频）

## 使用方法

### 自动发现所有交易对（推荐）
```python
collector = MarketDataCollector(
    bus=bus,
    market_topic="market_ticks",
    pairs=None,  # None表示自动发现所有可用交易对
    collect_interval=12.0,
    collect_balance=True,
    collect_ticker=True,
    auto_discover_pairs=True  # 自动发现所有可用交易对
)
```

### 手动指定交易对
```python
collector = MarketDataCollector(
    bus=bus,
    market_topic="market_ticks",
    pairs=["BTC/USD", "ETH/USD", "SOL/USD"],  # 手动指定交易对
    collect_interval=12.0,
    collect_balance=True,
    collect_ticker=True,
    auto_discover_pairs=False  # 不使用自动发现
)
```

## 效果

1. **自动发现所有可用交易对**：系统会自动从Roostoo API获取所有可用交易对
2. **采集所有交易对的数据**：MarketDataCollector会采集所有交易对的ticker数据
3. **Agent收到所有交易对数据**：Agent会收到所有交易对的市场数据
4. **Prompt鼓励多币种交易**：Prompt明确要求分析和交易多种币种
5. **Agent可以比较和选择**：Agent可以根据技术指标、价格趋势等因素选择最优币种

## 注意事项

1. **API限频**：采集所有交易对会增加API调用次数，需要适当调整 `collect_interval`
2. **数据量**：所有交易对的数据量较大，需要确保系统有足够的内存和网络带宽
3. **性能**：如果交易对数量很多，可以考虑只采集主流币种（如BTC、ETH、SOL等）

## 后续优化建议

1. **智能筛选**：可以根据交易量、流动性等指标自动筛选主流币种
2. **动态调整**：可以根据市场情况动态调整要监控的交易对
3. **缓存优化**：可以缓存交易所信息，减少API调用次数

## 测试

运行 `dual_ai_example.py` 或 `run_production.py` 时，系统会自动发现所有可用交易对，并采集所有交易对的数据。Agent会收到所有交易对的市场数据，并可以根据这些数据做出交易决策。

## 相关文件

- `api/agents/market_collector.py` - 市场数据采集器
- `api/agents/base_agent.py` - Agent基类
- `api/agents/data_formatter.py` - 数据格式化器
- `prompts/natural_language_prompt.txt` - Agent系统提示
- `api/agents/dual_ai_example.py` - 双AI交易示例

