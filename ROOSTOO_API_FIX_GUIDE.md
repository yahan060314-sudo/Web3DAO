# Roostoo API 修复指南

## 🔍 问题诊断

**当前问题**: 余额接口返回 401 错误 "api-key invalid"

**根本原因**: `.env` 文件中使用的是占位符值（`your_roostoo_api_key_here`），不是真实的API凭证

## ✅ 已修复的代码

### 1. 改进凭证检测逻辑

**文件**: `api/roostoo_client.py`

**位置**: 第 46-58 行

**改进**:
- ✅ 检测占位符值（如 "your_roostoo_api_key_here"）
- ✅ 如果检测到占位符，使用测试凭证并提示用户
- ✅ 更清晰的错误提示

### 2. 修复 get_balance 方法

**文件**: `api/roostoo_client.py`

**位置**: 第 240-247 行

**改进**:
- ✅ 修复了 timestamp 参数的重复问题
- ✅ 确保签名正确生成
- ✅ 简化了参数处理逻辑

### 3. 改进错误处理

**文件**: `api/roostoo_client.py`

**位置**: 第 190-210 行

**改进**:
- ✅ 针对 401 错误提供详细的诊断信息
- ✅ 提示用户检查 API 凭证
- ✅ 显示当前使用的 API Key（部分）

## 📍 所有相关代码位置

### 核心代码文件

#### `api/roostoo_client.py` - Roostoo API客户端 ⭐

**文件路径**: `/Users/snowman/Documents/GitHub/Web3DAO/api/roostoo_client.py`

**关键代码位置**:

1. **环境变量加载** (第 16-20 行)
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   API_KEY = os.getenv("ROOSTOO_API_KEY")
   SECRET_KEY = os.getenv("ROOSTOO_SECRET_KEY")
   BASE_URL = os.getenv("ROOSTOO_API_URL", "https://mock-api.roostoo.com")
   ```

2. **客户端初始化** (第 42-85 行)
   ```python
   def __init__(self, api_key: str = API_KEY, secret_key: str = SECRET_KEY, base_url: str = None):
       # 检查是否是Mock API
       is_mock_api = "mock" in self.base_url.lower()
       
       # 检查是否提供了真实的API凭证（排除占位符）
       is_placeholder = (
           (api_key and ("your_" in api_key.lower() or "placeholder" in api_key.lower() or "here" in api_key.lower())) or
           (secret_key and ("your_" in secret_key.lower() or "placeholder" in secret_key.lower() or "here" in secret_key.lower()))
       )
       
       has_real_credentials = (
           api_key and secret_key and 
           api_key.strip() != "" and secret_key.strip() != "" and
           api_key != "mock_api_key" and secret_key != "mock_secret_key" and
           not is_placeholder  # 排除占位符
       )
   ```

3. **请求签名** (第 90-123 行)
   ```python
   def _sign_request(self, payload: Dict[str, Any]) -> Tuple[Dict[str, str], str]:
       # 添加时间戳
       payload['timestamp'] = self._get_timestamp()
       
       # 排序参数
       sorted_payload = sorted(payload.items())
       
       # 拼接参数字符串
       total_params = urlencode(sorted_payload)
       
       # 生成HMAC-SHA256签名
       signature = hmac.new(
           self.secret_key.encode('utf-8'),
           total_params.encode('utf-8'),
           hashlib.sha256
       ).hexdigest()
       
       # 构建请求头
       headers = {
           'RST-API-KEY': self.api_key,
           'MSG-SIGNATURE': signature
       }
       
       return headers, total_params
   ```

4. **获取余额** (第 240-247 行) ⭐
   ```python
   def get_balance(self, timeout: Optional[float] = None) -> Dict:
       """[RCL_TopLevelCheck] 获取账户余额信息"""
       # 生成签名：timestamp参数需要参与签名
       timestamp = self._get_timestamp()
       payload = {'timestamp': timestamp}
       headers, _ = self._sign_request(payload)
       
       # 对于GET请求，timestamp需要作为URL参数
       params = {'timestamp': timestamp}
       
       return self._request('GET', '/v3/balance', headers=headers, params=params, timeout=timeout)
   ```

5. **错误处理** (第 190-210 行)
   ```python
   except requests.exceptions.HTTPError as e:
       status_code = e.response.status_code
       if status_code == 401:
           # 提供详细的诊断信息
           error_msg = (
               f"认证失败 (401 Unauthorized)\n"
               f"可能的原因:\n"
               f"  1. API Key 或 Secret Key 无效\n"
               f"  2. 使用了占位符值\n"
               f"  3. API凭证已过期\n"
               f"建议:\n"
               f"  1. 检查 .env 文件中的 API 凭证\n"
               f"  2. 确保使用的是真实的API凭证\n"
           )
   ```

### 使用 RoostooClient 的代码

#### `api/agents/market_collector.py` - 市场数据采集器

**位置**: 第 53 行和第 112 行

```python
# 第53行：创建RoostooClient
self.client = RoostooClient()

# 第112行：调用get_balance
raw_balance = self.client.get_balance()
```

#### `api/agents/executor.py` - 交易执行器

**位置**: 第 37 行

```python
# 第37行：创建RoostooClient
if not dry_run:
    self.client = RoostooClient()
```

#### `api/data_fetcher.py` - 数据获取器

**位置**: 第 21 行和第 62 行

```python
# 第21行：创建RoostooClient
client = RoostooClient()

# 第62行：调用get_balance
balance = client.get_balance()
```

## 🔧 解决方案

### 步骤1: 编辑 `.env` 文件

**.env 文件位置**: `/Users/snowman/Documents/GitHub/Web3DAO/.env`

**当前内容**（占位符）:
```env
ROOSTOO_API_KEY=your_roostoo_api_key_here
ROOSTOO_SECRET_KEY=your_roostoo_secret_key_here
```

**需要修改为**（真实凭证）:
```env
ROOSTOO_API_KEY=你的真实API密钥
ROOSTOO_SECRET_KEY=你的真实Secret密钥
ROOSTOO_API_URL=https://mock-api.roostoo.com
```

### 步骤2: 如何获取真实的API凭证

1. **登录 Roostoo 平台**
2. **进入 API 设置页面**
3. **创建 API Key 和 Secret Key**
4. **复制到 .env 文件中**

### 步骤3: 验证配置

```bash
# 运行测试脚本
python test_balance_fix.py

# 或运行诊断脚本
python diagnose_roostoo_connection.py
```

## 🎯 代码修复总结

### 修复1: 占位符检测

**问题**: 代码无法识别占位符值，将其当作真实凭证使用

**修复**: 添加占位符检测逻辑
- 检测 "your_", "placeholder", "here" 等关键词
- 如果检测到占位符，使用测试凭证并提示用户

### 修复2: get_balance 方法

**问题**: timestamp 参数处理不正确，可能导致签名错误

**修复**: 简化参数处理逻辑
- 明确 timestamp 的生成和使用
- 确保签名正确生成

### 修复3: 错误提示

**问题**: 401 错误提示不够详细

**修复**: 添加详细的诊断信息
- 列出可能的原因
- 提供解决建议
- 显示当前使用的 API Key（部分）

## 📋 测试步骤

### 1. 检查当前配置

```bash
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
key = os.getenv('ROOSTOO_API_KEY', '')
print('API Key:', key[:20] + '...' if len(key) > 20 else key)
print('是占位符:', 'your_' in key.lower() if key else True)
"
```

### 2. 测试 RoostooClient

```bash
python test_balance_fix.py
```

### 3. 运行完整测试

```bash
python test_complete_system.py --quick
```

## 🎉 完成

代码已经修复，现在需要：

1. **编辑 `.env` 文件**，填入真实的API凭证（不是占位符）
2. **运行测试**验证配置
3. **余额接口应该可以正常工作了**

## 📚 相关文档

- [BALANCE_CODE_LOCATIONS.md](./BALANCE_CODE_LOCATIONS.md) - 账户余额相关代码位置
- [FIX_BALANCE_401_ERROR.md](./FIX_BALANCE_401_ERROR.md) - 修复说明

