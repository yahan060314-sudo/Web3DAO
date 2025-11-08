# 真实交易设置指南

## 当前实现状态

### ✅ 已实现真实下单功能

**代码位置**：
- `api/agents/executor.py` - 交易执行器，真正调用下单API
- `api/roostoo_client.py` - Roostoo API客户端，真正发送HTTP请求

**确认**：
- ✅ 代码逻辑是真实的，没有模拟或mock逻辑
- ✅ 会真正调用 `RoostooClient.place_order()`
- ✅ 会真正发送HTTP POST请求到API服务器

### ⚠️ 需要配置：API URL

**当前状态**：
- 默认使用 `https://mock-api.roostoo.com`（模拟API）
- 需要配置为真实的Roostoo API URL

## 配置真实交易

### 步骤1：获取真实的Roostoo API URL

**需要信息**：
- 真实的Roostoo生产环境API基础URL
- 例如：`https://api.roostoo.com` 或其他URL

**获取方式**：
1. 查看Roostoo官方API文档
2. 联系Roostoo技术支持
3. 检查Roostoo平台设置中的API信息

### 步骤2：配置环境变量

在 `.env` 文件中添加：

```env
# Roostoo API配置
ROOSTOO_API_KEY=your_roostoo_api_key
ROOSTOO_SECRET_KEY=your_roostoo_secret_key

# 真实API URL（替换为实际的URL）
ROOSTOO_API_URL=https://api.roostoo.com
```

**注意**：
- 如果不设置 `ROOSTOO_API_URL`，默认使用mock API（用于测试）
- 设置后，所有API请求都会发送到真实服务器

### 步骤3：验证配置

运行以下代码验证：

```python
from api.roostoo_client import RoostooClient

client = RoostooClient()
print(f"API URL: {client.base_url}")
print(f"API Key: {client.api_key[:10]}...")  # 只显示前10个字符

# 测试连接
server_time = client.check_server_time()
print(f"Server time: {server_time}")
```

**预期输出**：
- 如果使用真实API：`[RoostooClient] ✓ 使用真实API: https://api.roostoo.com`
- 如果使用mock API：`[RoostooClient] ⚠️ 使用模拟API: https://mock-api.roostoo.com`

## 测试模式 vs 真实交易

### 测试模式（dry_run=True）

```python
from api.agents.executor import TradeExecutor

executor = TradeExecutor(
    bus=bus,
    decision_topic="decisions",
    dry_run=True  # 测试模式，不会真正下单
)
```

**特点**：
- ✅ 只打印下单参数
- ✅ 不真正调用API
- ✅ 适合测试和开发

### 真实交易模式（dry_run=False，默认）

```python
from api.agents.executor import TradeExecutor

executor = TradeExecutor(
    bus=bus,
    decision_topic="decisions",
    dry_run=False  # 真实交易模式（默认）
)
```

**特点**：
- ✅ 真正调用API下单
- ✅ 真正执行交易
- ⚠️ 请确保API URL和密钥正确

## 安全检查清单

在启用真实交易前，请确认：

- [ ] ✅ API密钥和Secret Key已在 `.env` 文件中配置
- [ ] ✅ 真实的Roostoo API URL已配置（`ROOSTOO_API_URL`）
- [ ] ✅ 已测试API连接（`check_server_time()` 成功）
- [ ] ✅ 已测试获取余额（`get_balance()` 成功）
- [ ] ✅ 已确认API认证方式正确
- [ ] ✅ 已设置适当的风险控制（限频、资金管理等）
- [ ] ✅ 已备份重要数据

## 代码修改说明

### 1. `api/roostoo_client.py`

**修改**：
- ✅ 支持从环境变量 `ROOSTOO_API_URL` 读取API URL
- ✅ 默认使用mock API（用于测试）
- ✅ 初始化时打印当前使用的API URL

### 2. `api/agents/executor.py`

**修改**：
- ✅ 添加 `dry_run` 参数（默认False，真实交易）
- ✅ 测试模式下只打印参数，不真正下单
- ✅ 真实模式下真正调用API

### 3. `config/config.py`

**修改**：
- ✅ 支持从环境变量读取 `ROOSTOO_API_URL`

## 使用示例

### 示例1：真实交易（生产环境）

```python
# .env文件
ROOSTOO_API_URL=https://api.roostoo.com
ROOSTOO_API_KEY=your_key
ROOSTOO_SECRET_KEY=your_secret

# 代码
from api.agents.executor import TradeExecutor

executor = TradeExecutor(
    bus=bus,
    decision_topic="decisions",
    dry_run=False  # 真实交易
)
executor.start()
```

### 示例2：测试模式（开发环境）

```python
# .env文件（不设置ROOSTOO_API_URL，使用默认mock API）
ROOSTOO_API_KEY=test_key
ROOSTOO_SECRET_KEY=test_secret

# 代码
executor = TradeExecutor(
    bus=bus,
    decision_topic="decisions",
    dry_run=True  # 测试模式
)
executor.start()
```

## 缺少的信息

### 需要用户提供：

1. **真实的Roostoo API URL**
   - 当前未知，需要从Roostoo官方获取
   - 可能是：`https://api.roostoo.com` 或其他URL

2. **API环境确认**
   - 真实API的认证方式是否与mock API相同？
   - 是否需要额外的配置或权限？

3. **测试需求**
   - 是否需要区分测试环境和生产环境？
   - 是否需要添加额外的安全开关？

## 总结

✅ **代码已实现真实下单功能** - 没有模拟逻辑

✅ **支持环境变量配置** - 可以通过 `.env` 文件配置API URL

⚠️ **需要配置真实API URL** - 当前默认使用mock API

✅ **支持测试模式** - 可以通过 `dry_run=True` 进行安全测试

✅ **安全检查** - 初始化时会打印当前使用的API URL，便于确认

