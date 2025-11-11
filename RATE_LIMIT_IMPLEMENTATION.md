# 频率限制实现说明

## 📋 要求

根据比赛规则，需要遵守以下频率限制：
1. **API调用频率**：每分钟最多5次
2. **决策生成频率**：每分钟最多1次

## ✅ 实现方案

### 1. 频率限制器 (`utils/rate_limiter.py`)

创建了通用的频率限制器类 `RateLimiter`，使用滑动窗口算法：
- `API_RATE_LIMITER`: 每分钟最多5次API调用
- `DECISION_RATE_LIMITER`: 每分钟最多1次决策生成

### 2. API调用频率限制

#### 2.1 RoostooClient (`api/roostoo_client.py`)
- 在 `_request()` 方法中添加了API调用频率限制
- 如果超过限制，会自动等待直到可以调用
- 所有API调用（`get_ticker`, `get_balance`, `place_order`等）都会受到限制

#### 2.2 MarketDataCollector (`api/agents/market_collector.py`)
- 默认采集间隔从 `5.0` 秒改为 `12.0` 秒
- 计算：每分钟60秒 ÷ 5次 = 12秒间隔
- 每次采集会调用：
  - `get_ticker()` - 每个交易对一次
  - `get_balance()` - 一次
- 如果只有一个交易对，每12秒调用2次API = 每分钟10次，但通过 `RoostooClient` 的频率限制器会自动控制

### 3. 决策生成频率限制

#### 3.1 BaseAgent (`api/agents/base_agent.py`)
- 默认决策间隔从 `10.0` 秒改为 `60.0` 秒（每分钟1次）
- 在 `_generate_decision()` 方法中添加了决策频率限制检查
- 如果超过限制，会跳过本次决策生成并打印警告

### 4. 配置更新

#### 4.1 run_production.py
- `MarketDataCollector` 的 `collect_interval` 从 `5.0` 改为 `12.0` 秒

## 🔍 验证

### API调用频率验证
- ✅ `RoostooClient._request()` 包含频率限制检查
- ✅ 所有API调用都会经过 `_request()` 方法
- ✅ `MarketDataCollector` 使用12秒间隔（理论每分钟5次，但实际可能更少因为频率限制器）

### 决策生成频率验证
- ✅ `BaseAgent.decision_interval` 默认60秒
- ✅ `_generate_decision()` 包含频率限制检查
- ✅ 即使 `decision_interval` 设置更短，频率限制器也会阻止超过限制的决策

## 📊 频率限制详情

### API调用限制
- **限制**：每分钟最多5次
- **实现位置**：`RoostooClient._request()`
- **机制**：滑动窗口，自动等待

### 决策生成限制
- **限制**：每分钟最多1次
- **实现位置**：`BaseAgent._generate_decision()`
- **机制**：滑动窗口，超过限制时跳过

## ⚠️ 注意事项

1. **多个Agent的情况**：
   - 所有Agent共享同一个 `DECISION_RATE_LIMITER`
   - 如果多个Agent同时尝试生成决策，只有第一个会成功，其他的会被限制

2. **API调用计算**：
   - `MarketDataCollector` 每12秒调用2次API（ticker + balance）
   - 理论每分钟10次，但 `RoostooClient` 的频率限制器会确保不超过5次/分钟
   - 如果超过限制，会自动等待

3. **时间精度**：
   - 频率限制器使用 `time.time()` 记录调用时间
   - 精度为秒级，足够满足需求

## 🧪 测试建议

1. **测试API频率限制**：
   ```python
   from api.roostoo_client import RoostooClient
   client = RoostooClient()
   # 快速连续调用6次，应该看到频率限制警告
   for i in range(6):
       client.get_ticker("BTC/USD")
   ```

2. **测试决策频率限制**：
   ```python
   # 创建Agent并快速触发多次决策
   # 应该看到决策频率限制警告
   ```

## 📝 修改文件清单

1. ✅ `utils/rate_limiter.py` - 新建频率限制器
2. ✅ `api/roostoo_client.py` - 添加API调用频率限制
3. ✅ `api/agents/market_collector.py` - 更新默认采集间隔
4. ✅ `api/agents/base_agent.py` - 更新默认决策间隔，添加频率限制检查
5. ✅ `run_production.py` - 更新采集间隔配置

