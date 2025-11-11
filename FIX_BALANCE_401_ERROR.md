# 修复余额接口 401 错误

## 🔍 问题分析

### 问题现象

```
[RoostooClient] ✗ HTTP错误: 401 - Unauthorized
    URL: https://mock-api.roostoo.com/v3/balance?timestamp=1762845353051
    响应内容: api-key invalid
```

### 问题原因

1. **Mock API 需要有效凭证**: 即使使用 Mock API，余额接口也需要有效的 API 凭证
2. **代码逻辑问题**: 原代码在 Mock API 模式下自动使用测试凭证，忽略了 `.env` 文件中的真实凭证
3. **环境变量加载问题**: `.env` 文件中的凭证可能没有被正确加载

## ✅ 解决方案

### 1. 代码修复（已完成）

**修改文件**: `api/roostoo_client.py`

**改进逻辑**:
- ✅ 检查是否提供了真实的 API 凭证
- ✅ 如果提供了真实凭证，即使在 Mock API 模式下也使用真实凭证
- ✅ 只有在没有提供任何凭证的情况下，才使用测试凭证
- ✅ 更清晰的提示信息

### 2. 配置 `.env` 文件

**重要**: 即使使用 Mock API，余额接口也需要有效的 API 凭证！

在项目根目录的 `.env` 文件中配置：

```env
# Roostoo API 配置
ROOSTOO_API_KEY=你的真实API密钥
ROOSTOO_SECRET_KEY=你的真实Secret密钥
ROOSTOO_API_URL=https://mock-api.roostoo.com

# 其他配置...
DEEPSEEK_API_KEY=你的DeepSeek API密钥
QWEN_API_KEY=你的Qwen API密钥
LLM_PROVIDER=deepseek
```

### 3. 验证配置

运行测试脚本：

```bash
python test_balance_fix.py
```

或直接测试：

```python
from api.roostoo_client import RoostooClient

# 创建客户端（会自动使用.env中的凭证）
client = RoostooClient()

# 测试获取余额
try:
    balance = client.get_balance(timeout=30.0)
    print(f"✓ 余额获取成功: {balance}")
except Exception as e:
    print(f"✗ 余额获取失败: {e}")
```

## 📍 账户余额相关代码位置

### 1. 获取余额接口

**文件**: `api/roostoo_client.py`

**位置**: 第 217-222 行

```python
def get_balance(self, timeout: Optional[float] = None) -> Dict:
    """[RCL_TopLevelCheck] 获取账户余额信息"""
    headers, _ = self._sign_request({})
    params = {'timestamp': self._get_timestamp()}
    return self._request('GET', '/v3/balance', headers=headers, params=params, timeout=timeout)
```

### 2. 签名请求方法

**文件**: `api/roostoo_client.py`

**位置**: 第 80-100 行

```python
def _sign_request(self, payload: Dict[str, Any]) -> Tuple[Dict[str, str], str]:
    """为RCL_TopLevelCheck请求生成签名和头部"""
    # 1. 添加时间戳
    payload['timestamp'] = self._get_timestamp()
    
    # 2. 排序参数
    sorted_payload = sorted(payload.items())
    
    # 3. 拼接参数字符串
    total_params = urlencode(sorted_payload)
    
    # 4. 生成HMAC-SHA256签名
    signature = hmac.new(
        self.secret_key.encode('utf-8'),
        total_params.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # 5. 构建请求头
    headers = {
        'RST-API-KEY': self.api_key,
        'MSG-SIGNATURE': signature
    }
    
    return headers, total_params
```

### 3. 市场数据采集器（使用余额）

**文件**: `api/agents/market_collector.py`

**位置**: 第 109-130 行

```python
def _collect_balance(self):
    """采集账户余额数据"""
    try:
        raw_balance = self.client.get_balance()
        formatted_balance = self.formatter.format_balance(raw_balance)
        # ...
    except Exception as e:
        print(f"[MarketDataCollector] Error fetching balance: {e}")
```

### 4. 余额数据格式化

**文件**: `api/agents/data_formatter.py`

**位置**: 第 128-196 行

```python
@staticmethod
def format_balance(raw_balance: Dict[str, Any]) -> Dict[str, Any]:
    """格式化账户余额数据"""
    # 处理Roostoo的SpotWallet格式
    spot_wallet = data.get("SpotWallet", {})
    # ...
```

### 5. Prompt管理器（使用余额）

**文件**: `api/agents/prompt_manager.py`

**位置**: 第 316-376 行

```python
def create_spot_prompt_from_market_data(
    self,
    market_snapshot: Dict[str, Any],
    ...
) -> Optional[str]:
    """从市场快照数据创建现货交易prompt"""
    balance = market_snapshot.get("balance")
    account_equity = str(balance.get("total_balance", "0")) if balance else "0"
    available_cash = str(balance.get("available_balance", "0")) if balance else "0"
    # ...
```

## 🔧 修复步骤

### 步骤1: 检查 `.env` 文件

确认 `.env` 文件在项目根目录，并包含：

```env
ROOSTOO_API_KEY=你的真实API密钥
ROOSTOO_SECRET_KEY=你的真实Secret密钥
ROOSTOO_API_URL=https://mock-api.roostoo.com
```

### 步骤2: 验证环境变量加载

```bash
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

print('ROOSTOO_API_KEY:', '✓ 已配置' if os.getenv('ROOSTOO_API_KEY') else '✗ 未配置')
print('ROOSTOO_SECRET_KEY:', '✓ 已配置' if os.getenv('ROOSTOO_SECRET_KEY') else '✗ 未配置')
"
```

### 步骤3: 测试余额接口

```bash
python test_balance_fix.py
```

### 步骤4: 运行完整测试

```bash
python test_complete_system.py --quick
```

## 🎯 关键点

1. **Mock API 也需要真实凭证**: Mock API 的余额接口需要有效的 API 凭证
2. **代码已修复**: 代码现在会优先使用 `.env` 文件中的真实凭证
3. **配置要求**: 确保 `.env` 文件中配置了有效的 API 凭证

## 📋 配置示例

### Mock API + 真实凭证（推荐）

```env
# 使用Mock API，但需要真实凭证用于余额接口
ROOSTOO_API_KEY=你的真实API密钥
ROOSTOO_SECRET_KEY=你的真实Secret密钥
ROOSTOO_API_URL=https://mock-api.roostoo.com
```

### 真实 API + 真实凭证

```env
# 使用真实API
ROOSTOO_API_KEY=你的真实API密钥
ROOSTOO_SECRET_KEY=你的真实Secret密钥
ROOSTOO_API_URL=https://api.roostoo.com
```

## 🔍 故障排查

### 问题1: 环境变量未加载

**症状**: 测试显示"ROOSTOO_API_KEY: ✗ 未配置"

**解决方案**:
1. 检查 `.env` 文件是否在项目根目录
2. 检查 `.env` 文件格式是否正确（没有多余的空格或引号）
3. 检查 `.env` 文件是否被 `.gitignore` 忽略（这是正常的）

### 问题2: 仍然返回 401 错误

**症状**: 配置了凭证但仍然返回 401

**解决方案**:
1. 检查 API 凭证是否正确
2. 检查 API 凭证是否有效
3. 检查 API 服务器状态
4. 检查网络连接

### 问题3: Mock API 不支持余额接口

**症状**: 即使使用真实凭证，Mock API 仍然返回错误

**解决方案**:
1. 确认 Mock API 是否支持余额接口
2. 尝试使用真实 API: `ROOSTOO_API_URL=https://api.roostoo.com`
3. 联系 API 提供商确认 Mock API 的功能

## 🎉 完成

修复完成后，余额接口应该可以正常工作了！

**验证**:
```bash
python test_balance_fix.py
```

预期输出:
```
✓ 余额获取成功!
响应键: ['Success', 'ErrMsg', 'data', ...]
✓ 找到SpotWallet数据
```

