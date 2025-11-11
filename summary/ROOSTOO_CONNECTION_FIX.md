# Roostoo API 连接问题修复说明

## 🔍 问题分析

### 问题1: 连接超时

**错误信息**:
```
HTTPSConnectionPool(host='api.roostoo.com', port=443): Read timed out. (read timeout=10)
```

**原因**:
1. 默认超时时间太短（10秒）
2. 网络连接慢或不稳定
3. API服务器响应慢
4. 没有重试机制

### 问题2: Balance为None

**错误信息**:
```
AttributeError: 'NoneType' object has no attribute 'get'
```

**原因**:
1. API连接失败导致无法获取余额数据
2. `prompt_manager.py` 没有处理 `balance` 为 `None` 的情况
3. 数据格式化时没有检查 `None` 值

## ✅ 修复方案

### 1. 增加超时时间和重试机制

**修改文件**: `api/roostoo_client.py`

**改进**:
- ✅ 默认超时时间从10秒增加到30秒
- ✅ 添加重试机制（默认3次）
- ✅ 指数退避策略（1秒、2秒、3秒）
- ✅ 详细的错误信息和建议

**代码变更**:
```python
def _request(self, method: str, path: str, timeout: Optional[float] = None, max_retries: int = 3, retry_delay: float = 1.0, **kwargs):
    # 使用配置的超时时间，如果未指定则使用30秒
    if timeout is None:
        timeout = 30.0
    
    # 重试机制
    for attempt in range(max_retries):
        try:
            response = self.session.request(method, url, **kwargs, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout as e:
            # 重试逻辑...
```

### 2. 修复Balance为None的问题

**修改文件**: `api/agents/prompt_manager.py`

**改进**:
- ✅ 检查 `balance` 是否为 `None`
- ✅ 检查 `balance` 是否为字典类型
- ✅ 提供默认值（"0"）
- ✅ 安全的字典访问

**代码变更**:
```python
# 提取账户信息
balance = market_snapshot.get("balance")
# 处理balance为None的情况
if balance is None:
    balance = {}
elif not isinstance(balance, dict):
    balance = {}

account_equity = str(balance.get("total_balance", "0")) if balance else "0"
available_cash = str(balance.get("available_balance", "0")) if balance else "0"
```

### 3. 改进错误处理

**改进**:
- ✅ 详细的错误信息
- ✅ 具体的建议和解决方案
- ✅ 区分不同类型的错误（超时、连接错误、HTTP错误）

## 🔧 使用方法

### 1. 测试连接

```bash
# 测试Roostoo API连接
python test_real_api.py
```

### 2. 检查网络连接

```bash
# 检查DNS解析
ping api.roostoo.com

# 检查端口连接
telnet api.roostoo.com 443
```

### 3. 增加超时时间（如果需要）

```python
from api.roostoo_client import RoostooClient

client = RoostooClient()

# 使用更长的超时时间（60秒）
server_time = client.check_server_time(timeout=60.0)
```

## 📋 故障排查步骤

### 步骤1: 检查网络连接

```bash
# 1. 检查DNS解析
ping api.roostoo.com

# 2. 检查端口连接
curl -v https://api.roostoo.com/v3/serverTime

# 3. 检查防火墙设置
# (根据你的操作系统)
```

### 步骤2: 检查API凭证

```bash
# 检查环境变量
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

print('ROOSTOO_API_KEY:', '✓' if os.getenv('ROOSTOO_API_KEY') else '✗')
print('ROOSTOO_SECRET_KEY:', '✓' if os.getenv('ROOSTOO_SECRET_KEY') else '✗')
print('ROOSTOO_API_URL:', os.getenv('ROOSTOO_API_URL', 'Not set'))
"
```

### 步骤3: 测试API连接

```python
from api.roostoo_client import RoostooClient

try:
    client = RoostooClient()
    # 测试服务器时间（不需要认证）
    server_time = client.check_server_time(timeout=60.0)
    print(f"✓ 服务器时间: {server_time}")
except Exception as e:
    print(f"✗ 连接失败: {e}")
```

### 步骤4: 检查API服务器状态

```bash
# 检查API服务器是否可用
curl -X GET "https://api.roostoo.com/v3/serverTime"
```

## 🔍 可能的原因和解决方案

### 原因1: 网络连接慢

**解决方案**:
1. 增加超时时间（已修复，默认30秒）
2. 检查网络连接
3. 使用VPN或更换网络
4. 检查代理设置

### 原因2: API服务器响应慢

**解决方案**:
1. 增加超时时间
2. 使用重试机制（已修复）
3. 检查API服务器状态
4. 联系API提供商

### 原因3: 防火墙阻止连接

**解决方案**:
1. 检查防火墙设置
2. 允许连接到 `api.roostoo.com:443`
3. 检查代理设置
4. 使用VPN

### 原因4: DNS解析失败

**解决方案**:
1. 检查DNS设置
2. 使用公共DNS（如8.8.8.8）
3. 检查 `/etc/hosts` 文件
4. 清除DNS缓存

### 原因5: API服务器暂时不可用

**解决方案**:
1. 等待一段时间后重试
2. 检查API服务器状态页面
3. 联系API提供商
4. 使用重试机制（已修复）

## 📝 配置建议

### 1. 环境变量配置

```env
# Roostoo API
ROOSTOO_API_KEY=your_api_key
ROOSTOO_SECRET_KEY=your_secret_key
ROOSTOO_API_URL=https://api.roostoo.com

# 可选：自定义超时时间（秒）
ROOSTOO_TIMEOUT=60
```

### 2. 代码配置

```python
from api.roostoo_client import RoostooClient

# 使用自定义超时时间
client = RoostooClient()

# 测试连接（使用60秒超时）
try:
    server_time = client.check_server_time(timeout=60.0)
    print(f"✓ 连接成功: {server_time}")
except Exception as e:
    print(f"✗ 连接失败: {e}")
```

## 🎯 测试验证

### 1. 运行测试

```bash
# 运行完整测试
python test_complete_system.py --quick
```

### 2. 检查输出

**成功输出**:
```
✓ Roostoo API connection test passed
✓ Balance formatted successfully
```

**失败输出**:
```
✗ Roostoo API test failed: [错误信息]
[详细的错误信息和建议]
```

## 💡 提示

1. **超时时间**: 如果网络较慢，可以增加超时时间（默认30秒）
2. **重试机制**: 系统会自动重试3次，每次间隔递增
3. **错误处理**: 所有错误都会提供详细的诊断信息
4. **网络检查**: 建议先检查网络连接，再测试API

## 📚 相关文档

- [HOW_TO_TEST_COMPLETE_FLOW.md](./HOW_TO_TEST_COMPLETE_FLOW.md) - 完整流程测试指南
- [SETUP_REAL_API.md](./SETUP_REAL_API.md) - 真实API设置指南
- [TEST_OUTPUT_EXPLANATION.md](./TEST_OUTPUT_EXPLANATION.md) - 测试输出说明

