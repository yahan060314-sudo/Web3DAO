# collect_interval 优化方案

## 问题分析

### 原有问题
1. **固定间隔不灵活**：`collect_interval=12.0` 秒是固定值，无法根据交易对数量动态调整
2. **API调用过多**：如果有很多交易对（如10个），每次循环需要调用10+次API，但API限频只有3次/分钟
3. **资源浪费**：即使价格没有变化，也会发布数据，增加系统负载
4. **无法扩展**：交易对数量增加时，固定间隔会导致API调用超出限制

### API限频约束
- **API限频**：每分钟最多3次调用（`utils/rate_limiter.py`）
- **频率限制器**：`RoostooClient` 使用 `API_RATE_LIMITER` 自动控制调用频率
- **自动等待**：如果超过限制，频率限制器会自动等待

## 优化方案

### 1. 分批采集（Batch Collection）
- **原理**：每次循环只采集部分交易对，轮换采集所有交易对
- **优势**：
  - 减少单次循环的API调用次数
  - 确保所有交易对都能被采集到
  - 避免一次性调用太多API导致限频

**实现**：
```python
batch_size = 3  # 每次循环采集3个交易对
# 如果有10个交易对，需要4个循环才能采集完所有交易对
# 循环1: 采集 BTC/USD, ETH/USD, SOL/USD
# 循环2: 采集 BNB/USD, ADA/USD, DOT/USD
# 循环3: 采集 MATIC/USD, AVAX/USD, LINK/USD
# 循环4: 采集 UNI/USD
```

### 2. 自动计算采集间隔
- **原理**：根据交易对数量、批次大小、API限频自动计算最优间隔
- **公式**：
  ```
  calls_per_cycle = batch_size + (1 if collect_balance else 0)
  theoretical_min_interval = (time_window / max_calls_per_minute) * calls_per_cycle * 1.2
  collect_interval = max(20.0, min(60.0, theoretical_min_interval))
  ```
- **约束**：
  - 最小间隔：20秒（避免过于频繁）
  - 最大间隔：60秒（避免数据过旧）
  - 安全系数：1.2（确保有缓冲）

**示例计算**：
- 交易对数量：10个
- 批次大小：3个
- 采集余额：是
- 每次循环API调用：3 + 1 = 4次
- API限频：3次/60秒
- 理论最小间隔：(60 / 3) * 4 * 1.2 = 96秒
- 实际间隔：min(96, 60) = 60秒（受最大间隔限制）

### 3. 价格变化阈值
- **原理**：只在价格变化超过阈值时发布数据，减少重复数据
- **阈值**：0.1%（价格变化超过0.1%才发布）
- **优势**：
  - 减少消息总线负载
  - 减少Agent处理的数据量
  - 提高系统效率

### 4. 动态更新交易所信息
- **原理**：根据交易对数量动态调整交易所信息的更新频率
- **公式**：
  ```python
  exchange_info_interval = max(20, len(pairs) // batch_size * 2)
  ```
- **优势**：
  - 避免频繁调用 `get_exchange_info()`
  - 确保交易对列表及时更新

## 配置参数

### MarketDataCollector 参数
```python
collector = MarketDataCollector(
    bus=bus,
    market_topic="market_ticks",
    pairs=None,  # None表示自动发现所有可用交易对
    collect_interval=None,  # None表示根据交易对数量自动计算最优间隔
    collect_balance=True,
    collect_ticker=True,
    auto_discover_pairs=True,  # 自动发现所有可用交易对
    batch_size=3  # 每次循环采集3个交易对（默认值）
)
```

### 参数说明
- **pairs**: 交易对列表，`None` 表示自动发现
- **collect_interval**: 采集间隔（秒），`None` 表示自动计算
- **batch_size**: 每次循环采集的交易对数量，默认3个
- **auto_discover_pairs**: 是否自动发现所有可用交易对，默认True

## 性能分析

### 场景1：少量交易对（3个）
- 批次大小：3个
- 每次循环API调用：3 + 1 = 4次
- 理论间隔：96秒
- 实际间隔：60秒（受最大间隔限制）
- 完整轮换：1个循环（60秒）

### 场景2：中等交易对（10个）
- 批次大小：3个
- 每次循环API调用：3 + 1 = 4次
- 理论间隔：96秒
- 实际间隔：60秒（受最大间隔限制）
- 完整轮换：4个循环（240秒 = 4分钟）

### 场景3：大量交易对（30个）
- 批次大小：3个
- 每次循环API调用：3 + 1 = 4次
- 理论间隔：96秒
- 实际间隔：60秒（受最大间隔限制）
- 完整轮换：10个循环（600秒 = 10分钟）

## 优化效果

### 1. API调用优化
- **之前**：如果有10个交易对，每次循环调用10+次API，超出限制
- **之后**：每次循环只调用4次API，符合限频要求

### 2. 数据采集优化
- **之前**：所有交易对同时采集，可能导致数据过时
- **之后**：分批采集，确保所有交易对都能及时更新

### 3. 系统负载优化
- **之前**：即使价格没有变化，也会发布数据
- **之后**：只在价格变化超过0.1%时发布，减少负载

### 4. 扩展性优化
- **之前**：交易对数量增加时，固定间隔会导致问题
- **之后**：自动调整间隔，适应不同数量的交易对

## 使用建议

### 1. 默认配置（推荐）
```python
collector = MarketDataCollector(
    bus=bus,
    market_topic="market_ticks",
    pairs=None,  # 自动发现
    collect_interval=None,  # 自动计算
    batch_size=3  # 默认批次大小
)
```

### 2. 手动指定交易对
```python
collector = MarketDataCollector(
    bus=bus,
    market_topic="market_ticks",
    pairs=["BTC/USD", "ETH/USD", "SOL/USD"],  # 手动指定
    collect_interval=None,  # 自动计算
    batch_size=3
)
```

### 3. 自定义批次大小
```python
collector = MarketDataCollector(
    bus=bus,
    market_topic="market_ticks",
    pairs=None,
    collect_interval=None,
    batch_size=5  # 增大批次大小（如果API限频允许）
)
```

### 4. 固定间隔（不推荐）
```python
collector = MarketDataCollector(
    bus=bus,
    market_topic="market_ticks",
    pairs=None,
    collect_interval=30.0,  # 固定30秒间隔
    batch_size=3
)
```

## 注意事项

1. **API限频**：即使有频率限制器自动控制，也不应该设置过于频繁的间隔
2. **数据 freshness**：间隔越大，数据越可能过时，但可以减少API调用
3. **批次大小**：批次大小越大，单次循环调用越多，但完整轮换越快
4. **价格变化阈值**：0.1%的阈值可以根据需要调整，但不要设置太小（会导致频繁发布）

## 监控和调试

### 查看采集状态
```
[MarketDataCollector] 自动计算采集间隔: 60.0秒
  - 交易对数量: 10
  - 批次大小: 3 个/循环
  - 每次循环API调用: 4 次 (ticker: 3, balance: 1)
  - API限频: 3次/60秒
  - 完整轮换: 4 个循环 (240.0秒)
```

### 查看批次进度
```
[MarketDataCollector] 批次进度: 1/4 (本次采集: BTC/USD, ETH/USD, SOL/USD)
[MarketDataCollector] 批次进度: 2/4 (本次采集: BNB/USD, ADA/USD, DOT/USD)
```

## 后续优化建议

1. **智能筛选**：可以根据交易量、流动性等指标自动筛选主流币种
2. **动态调整**：可以根据市场情况动态调整批次大小和采集间隔
3. **优先级队列**：可以给主流币种更高的采集优先级
4. **缓存优化**：可以缓存交易所信息，减少API调用次数

