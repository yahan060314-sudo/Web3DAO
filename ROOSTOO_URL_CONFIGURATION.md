# Roostoo API URL 配置说明

## ✅ 当前配置

**默认 URL**: `https://mock-api.roostoo.com` (Mock API，用于测试)

## 🔧 如何配置 URL

### 方法1: 在 .env 文件中设置（推荐）

打开 `.env` 文件，添加或修改：

```env
# 使用 Mock API（测试环境，不会真正下单）
ROOSTOO_API_URL=https://mock-api.roostoo.com

# 或使用真实 API（生产环境，会真正下单）
# ROOSTOO_API_URL=https://api.roostoo.com
```

### 方法2: 在代码中直接设置

```python
from api.roostoo_client import RoostooClient

# 使用 Mock API
client = RoostooClient(base_url="https://mock-api.roostoo.com")

# 或使用真实 API
# client = RoostooClient(base_url="https://api.roostoo.com")
```

## 🔍 检查当前配置

运行检查脚本：

```bash
python check_roostoo_url.py
```

或使用 Python 代码：

```python
import os
from dotenv import load_dotenv
load_dotenv()

env_url = os.getenv("ROOSTOO_API_URL")
default_url = "https://mock-api.roostoo.com"
actual_url = env_url if env_url else default_url

print(f"环境变量 ROOSTOO_API_URL: {env_url if env_url else '未设置'}")
print(f"代码默认 URL: {default_url}")
print(f"实际使用的 URL: {actual_url}")
```

## 📋 URL 类型说明

### Mock API (测试环境)

- **URL**: `https://mock-api.roostoo.com`
- **用途**: 测试和开发
- **特点**: 
  - 不会真正下单
  - 返回模拟数据
  - 适合测试和开发

### 真实 API (生产环境)

- **URL**: `https://api.roostoo.com`
- **用途**: 生产环境
- **特点**: 
  - 会真正下单
  - 返回真实数据
  - 需要有效的API凭证

## ✅ 验证配置

### 1. 检查 URL 配置

```bash
python check_roostoo_url.py
```

### 2. 测试连接

```bash
python diagnose_roostoo_connection.py
```

### 3. 运行测试

```bash
python test_complete_system.py --quick
```

## 🎯 快速修复

如果发现使用了错误的 URL，请：

1. **检查 .env 文件**:
   ```bash
   cat .env | grep ROOSTOO_API_URL
   ```

2. **修改 .env 文件**:
   ```bash
   # 编辑 .env 文件，确保使用 Mock API
   ROOSTOO_API_URL=https://mock-api.roostoo.com
   ```

3. **验证配置**:
   ```bash
   python check_roostoo_url.py
   ```

## 📝 注意事项

1. **环境变量优先级**: 如果设置了 `ROOSTOO_API_URL` 环境变量，会优先使用环境变量的值
2. **默认值**: 如果没有设置环境变量，默认使用 `https://mock-api.roostoo.com`
3. **代码参数**: 如果直接在代码中传入 `base_url` 参数，会优先使用参数值

## 🔄 修改后的文件

以下文件的默认 URL 已更新为 `https://mock-api.roostoo.com`:

- ✅ `api/roostoo_client.py` - Roostoo客户端
- ✅ `config/config.py` - 配置文件
- ✅ `diagnose_roostoo_connection.py` - 诊断脚本

## 🎉 完成

现在默认使用 Mock API (`https://mock-api.roostoo.com`)，可以安全地进行测试，不会真正下单。

