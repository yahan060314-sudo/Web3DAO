# Roostoo API 连接问题排查指南

## 🔍 问题分析

根据你的错误信息：

```
HTTPSConnectionPool(host='api.roostoo.com', port=443): Read timed out. (read timeout=10)
```

### 可能的原因

1. **网络连接慢或不稳定**
   - 网络延迟高
   - 网络不稳定
   - 带宽不足

2. **API服务器响应慢**
   - API服务器负载高
   - API服务器暂时不可用
   - API服务器维护中

3. **防火墙或代理设置**
   - 防火墙阻止HTTPS连接
   - 代理设置不正确
   - 企业网络限制

4. **超时时间设置太短**
   - 默认超时时间10秒可能不够
   - 需要更长的超时时间

5. **DNS解析问题**
   - DNS服务器响应慢
   - DNS缓存问题
   - DNS配置错误

## ✅ 已修复的问题

### 1. 增加超时时间和重试机制

**修改**: `api/roostoo_client.py`

**改进**:
- ✅ 默认超时时间从10秒增加到30秒
- ✅ 添加重试机制（默认3次）
- ✅ 指数退避策略
- ✅ 详细的错误信息

### 2. 修复Balance为None的问题

**修改**: `api/agents/prompt_manager.py`

**改进**:
- ✅ 检查 `balance` 是否为 `None`
- ✅ 提供默认值
- ✅ 安全的字典访问

## 🔧 排查步骤

### 步骤1: 运行诊断脚本

```bash
python diagnose_roostoo_connection.py
```

这个脚本会：
1. 测试网络连接
2. 测试API端点
3. 测试Roostoo客户端
4. 提供详细的诊断信息

### 步骤2: 检查网络连接

```bash
# 检查DNS解析
ping api.roostoo.com

# 检查HTTP连接
curl -v https://api.roostoo.com/v3/serverTime

# 检查端口连接
telnet api.roostoo.com 443
```

### 步骤3: 检查API凭证

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

### 步骤4: 测试API连接

```python
from api.roostoo_client import RoostooClient

try:
    client = RoostooClient()
    # 使用更长的超时时间（60秒）
    server_time = client.check_server_time(timeout=60.0)
    print(f"✓ 连接成功: {server_time}")
except Exception as e:
    print(f"✗ 连接失败: {e}")
```

## 🛠️ 解决方案

### 方案1: 增加超时时间（推荐）

**已自动修复**: 默认超时时间已从10秒增加到30秒，并添加了重试机制。

**手动配置**:
```python
from api.roostoo_client import RoostooClient

client = RoostooClient()

# 使用更长的超时时间
server_time = client.check_server_time(timeout=60.0)
ticker = client.get_ticker(pair="BTC/USD", timeout=60.0)
balance = client.get_balance(timeout=60.0)
```

### 方案2: 检查网络连接

```bash
# 1. 检查DNS解析
ping api.roostoo.com

# 2. 检查HTTP连接
curl -v https://api.roostoo.com/v3/serverTime

# 3. 检查防火墙设置
# (根据你的操作系统)
```

### 方案3: 使用代理（如果需要）

```python
import requests
from api.roostoo_client import RoostooClient

# 配置代理
proxies = {
    'http': 'http://proxy.example.com:8080',
    'https': 'https://proxy.example.com:8080'
}

client = RoostooClient()
client.session.proxies = proxies
```

### 方案4: 检查API服务器状态

```bash
# 检查API服务器是否可用
curl -X GET "https://api.roostoo.com/v3/serverTime"
```

## 📋 需要你提供的信息

为了更好地诊断问题，请提供以下信息：

### 1. 网络环境信息

```bash
# 运行诊断脚本
python diagnose_roostoo_connection.py

# 检查网络连接
ping api.roostoo.com

# 检查DNS
nslookup api.roostoo.com
```

### 2. 环境变量配置

请确认 `.env` 文件中的配置：

```env
ROOSTOO_API_KEY=your_api_key
ROOSTOO_SECRET_KEY=your_secret_key
ROOSTOO_API_URL=https://api.roostoo.com
```

### 3. 错误日志

请提供完整的错误日志，包括：
- 错误消息
- 堆栈跟踪
- 网络环境信息

### 4. 网络环境

- 是否使用VPN？
- 是否使用代理？
- 是否在企业网络中？
- 网络延迟如何？

## 🔍 常见问题

### 问题1: 连接超时

**症状**: `Read timed out. (read timeout=10)`

**解决方案**:
1. ✅ 已修复：增加超时时间到30秒
2. ✅ 已修复：添加重试机制
3. 检查网络连接
4. 检查防火墙设置
5. 尝试使用VPN或更换网络

### 问题2: 连接错误

**症状**: `ConnectionError` 或 `Connection refused`

**解决方案**:
1. 检查网络连接
2. 检查DNS设置
3. 检查防火墙设置
4. 检查代理设置
5. 尝试使用VPN

### 问题3: Balance为None

**症状**: `'NoneType' object has no attribute 'get'`

**解决方案**:
1. ✅ 已修复：处理balance为None的情况
2. 检查API连接
3. 检查API凭证
4. 检查API服务器状态

## 🎯 快速修复

### 立即尝试

1. **运行诊断脚本**:
   ```bash
   python diagnose_roostoo_connection.py
   ```

2. **检查网络连接**:
   ```bash
   ping api.roostoo.com
   curl -v https://api.roostoo.com/v3/serverTime
   ```

3. **重新运行测试**:
   ```bash
   python test_complete_system.py --quick
   ```

## 📚 相关文档

- [ROOSTOO_CONNECTION_FIX.md](./ROOSTOO_CONNECTION_FIX.md) - 修复说明
- [SETUP_REAL_API.md](./SETUP_REAL_API.md) - 真实API设置指南
- [TEST_OUTPUT_EXPLANATION.md](./TEST_OUTPUT_EXPLANATION.md) - 测试输出说明

## 💡 提示

1. **超时时间**: 如果网络较慢，系统会自动重试3次
2. **错误处理**: 所有错误都会提供详细的诊断信息
3. **网络检查**: 建议先运行诊断脚本，再测试API
4. **API状态**: 如果API服务器暂时不可用，请等待后重试

---

## 🚀 下一步

1. 运行诊断脚本: `python diagnose_roostoo_connection.py`
2. 根据诊断结果采取相应措施
3. 重新运行测试: `python test_complete_system.py --quick`
4. 如果问题持续，请提供诊断脚本的完整输出

