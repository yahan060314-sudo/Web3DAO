# 修复 Roostoo API 连接问题

## 🔍 问题诊断

根据诊断结果，问题在于：

1. ✅ **网络连接正常** - Mock API 服务器可以访问
2. ✅ **API端点正常** - `/v3/serverTime` 可以正常响应
3. ❌ **API凭证未配置** - `.env` 文件中缺少 `ROOSTOO_API_KEY` 和 `ROOSTOO_SECRET_KEY`

## ✅ 解决方案

### 方案1: 使用 Mock API（推荐用于测试）

**已修复**: 代码已更新，Mock API 模式下可以使用测试凭证或空凭证。

**使用方法**:
```python
from api.roostoo_client import RoostooClient

# Mock API 模式下，可以不提供凭证（会自动使用测试凭证）
client = RoostooClient()

# 或明确使用 Mock API
client = RoostooClient(base_url="https://mock-api.roostoo.com")
```

### 方案2: 配置真实的 API 凭证

如果使用真实 API，需要在 `.env` 文件中配置：

```env
ROOSTOO_API_KEY=你的真实API密钥
ROOSTOO_SECRET_KEY=你的真实Secret密钥
ROOSTOO_API_URL=https://api.roostoo.com
```

### 方案3: 在代码中直接提供凭证

```python
from api.roostoo_client import RoostooClient

# 使用真实API凭证
client = RoostooClient(
    api_key="你的API密钥",
    secret_key="你的Secret密钥",
    base_url="https://api.roostoo.com"
)
```

## 🔧 代码修复

### 修复内容

1. **Mock API 模式支持空凭证**:
   - Mock API 模式下，如果没有提供凭证，自动使用测试凭证
   - 真实 API 模式下，仍然要求有效的凭证

2. **改进的错误提示**:
   - 更清晰的错误信息
   - 区分 Mock API 和真实 API 的行为

### 修改的文件

- `api/roostoo_client.py` - 更新了 `__init__` 方法，支持 Mock API 模式下的空凭证

## 📋 测试步骤

### 1. 测试 Mock API 连接

```bash
# 运行诊断脚本
python diagnose_roostoo_connection.py

# 或运行完整测试
python test_complete_system.py --quick
```

### 2. 验证连接

```python
from api.roostoo_client import RoostooClient

# 测试 Mock API（不需要凭证）
client = RoostooClient()
server_time = client.check_server_time(timeout=30.0)
print(f"✓ 服务器时间: {server_time}")

# 测试获取市场数据
ticker = client.get_ticker('BTC/USD', timeout=30.0)
print(f"✓ 市场数据: {ticker}")
```

## 🎯 常见问题

### 问题1: Mock API 连接超时

**原因**: 网络问题或 API 服务器响应慢

**解决方案**:
1. 检查网络连接
2. 增加超时时间（已默认设置为30秒）
3. 使用重试机制（已默认3次重试）

### 问题2: 真实 API 连接失败

**原因**: API 凭证错误或 API 服务器不可用

**解决方案**:
1. 检查 API 凭证是否正确
2. 检查 API URL 是否正确
3. 检查 API 服务器状态
4. 检查网络连接

### 问题3: Balance 获取失败

**原因**: API 认证失败或 API 服务器错误

**解决方案**:
1. 检查 API 凭证
2. 检查 API 权限
3. 检查 API 服务器状态
4. 对于 Mock API，某些端点可能返回模拟数据

## 📝 配置建议

### Mock API 配置（测试环境）

```env
# 可以不设置 API 凭证（Mock API 模式下会自动使用测试凭证）
# ROOSTOO_API_KEY=
# ROOSTOO_SECRET_KEY=
ROOSTOO_API_URL=https://mock-api.roostoo.com
```

### 真实 API 配置（生产环境）

```env
ROOSTOO_API_KEY=你的真实API密钥
ROOSTOO_SECRET_KEY=你的真实Secret密钥
ROOSTOO_API_URL=https://api.roostoo.com
```

## 🔍 故障排查

### 步骤1: 检查网络连接

```bash
# 测试 DNS 解析
ping mock-api.roostoo.com

# 测试 HTTP 连接
curl -v https://mock-api.roostoo.com/v3/serverTime
```

### 步骤2: 检查 API 配置

```bash
# 运行诊断脚本
python diagnose_roostoo_connection.py

# 检查 URL 配置
python check_roostoo_url.py
```

### 步骤3: 测试连接

```python
from api.roostoo_client import RoostooClient

try:
    client = RoostooClient()
    server_time = client.check_server_time(timeout=60.0)
    print(f"✓ 连接成功: {server_time}")
except Exception as e:
    print(f"✗ 连接失败: {e}")
```

## 🎉 完成

现在 Mock API 可以在没有凭证的情况下工作，适合测试和开发。

如果要使用真实 API，请确保在 `.env` 文件中配置了正确的 API 凭证。

