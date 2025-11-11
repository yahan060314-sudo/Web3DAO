# Roostoo API URL 更新说明

## ✅ 已更新

已将 Roostoo API URL 的默认值更新为 `https://mock-api.roostoo.com`

## 📋 修改的文件

### 1. `api/roostoo_client.py`

**修改内容**:
- 默认 URL: `https://mock-api.roostoo.com`
- 支持通过环境变量 `ROOSTOO_API_URL` 覆盖

### 2. `config/config.py`

**修改内容**:
- 默认 URL: `https://mock-api.roostoo.com`
- 添加了注释说明

### 3. `diagnose_roostoo_connection.py`

**修改内容**:
- 默认 URL: `https://mock-api.roostoo.com`
- 诊断脚本使用正确的默认 URL

## 🔧 使用方法

### 方法1: 使用默认 Mock API（推荐用于测试）

```python
from api.roostoo_client import RoostooClient

# 使用默认 Mock API
client = RoostooClient()
# 会自动使用 https://mock-api.roostoo.com
```

### 方法2: 通过环境变量配置

在 `.env` 文件中设置：

```env
# 使用 Mock API（测试）
ROOSTOO_API_URL=https://mock-api.roostoo.com

# 或使用真实 API（生产）
# ROOSTOO_API_URL=https://api.roostoo.com
```

### 方法3: 通过代码配置

```python
from api.roostoo_client import RoostooClient

# 使用 Mock API
client = RoostooClient(base_url="https://mock-api.roostoo.com")

# 或使用真实 API
# client = RoostooClient(base_url="https://api.roostoo.com")
```

## ✅ 验证

### 检查当前配置

```bash
python -c "
from api.roostoo_client import RoostooClient
import os
from dotenv import load_dotenv
load_dotenv()

client = RoostooClient()
print('当前使用的 URL:', client.base_url)
print('环境变量 ROOSTOO_API_URL:', os.getenv('ROOSTOO_API_URL', '未设置（使用默认值）'))
"
```

### 测试连接

```bash
# 运行诊断脚本
python diagnose_roostoo_connection.py

# 或运行完整测试
python test_complete_system.py --quick
```

## 📝 注意事项

1. **Mock API vs 真实 API**:
   - Mock API (`https://mock-api.roostoo.com`): 用于测试，不会真正下单
   - 真实 API (`https://api.roostoo.com`): 用于生产，会真正下单

2. **环境变量优先级**:
   - 如果设置了 `ROOSTOO_API_URL` 环境变量，会优先使用环境变量的值
   - 如果没有设置，则使用默认值 `https://mock-api.roostoo.com`

3. **代码中硬编码**:
   - 如果直接在代码中传入 `base_url` 参数，会优先使用参数值

## 🎯 测试

运行测试验证 URL 是否正确：

```bash
# 测试1: 检查 URL 配置
python -c "
from api.roostoo_client import RoostooClient
client = RoostooClient()
print('✓ 当前 URL:', client.base_url)
assert 'mock-api' in client.base_url, 'URL should be mock-api'
print('✓ URL 配置正确')
"

# 测试2: 运行完整测试
python test_complete_system.py --quick
```

## 🔍 相关文件

- `api/roostoo_client.py` - Roostoo客户端（已更新）
- `config/config.py` - 配置文件（已更新）
- `diagnose_roostoo_connection.py` - 诊断脚本（已更新）

