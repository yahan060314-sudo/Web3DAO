# 修复余额接口认证问题

## 🔍 问题分析

### 问题现象

```
[RoostooClient] ✗ HTTP错误: 401 - Unauthorized
    URL: https://mock-api.roostoo.com/v3/balance?timestamp=1762845353051
    响应内容: api-key invalid
```

### 问题原因

1. **Mock API 模式下的凭证问题**:
   - 代码检测到是 Mock API，就自动使用测试凭证（`mock_api_key` 和 `mock_secret_key`）
   - 即使 `.env` 文件中配置了真实的 API 凭证，也被忽略了
   - Mock API 的余额接口需要有效的 API 凭证才能工作

2. **代码逻辑问题**:
   - 原代码：Mock API 模式 → 使用测试凭证
   - 应该：Mock API 模式 + 有真实凭证 → 使用真实凭证

## ✅ 解决方案

### 修改逻辑

**修改文件**: `api/roostoo_client.py`

**改进**:
1. ✅ 检查是否提供了真实的 API 凭证
2. ✅ 如果提供了真实凭证，即使在 Mock API 模式下也使用真实凭证
3. ✅ 只有在没有提供任何凭证的情况下，才使用测试凭证
4. ✅ 更清晰的提示信息

### 修改后的逻辑

```python
# 检查是否是Mock API
is_mock_api = "mock" in self.base_url.lower()

# 检查是否提供了真实的API凭证
has_real_credentials = api_key and secret_key and api_key != "mock_api_key" and secret_key != "mock_secret_key"

if is_mock_api:
    if has_real_credentials:
        # 使用真实凭证（即使是在Mock API模式下）
        self.api_key = api_key
        self.secret_key = secret_key
    else:
        # 使用测试凭证（仅适用于公开接口）
        self.api_key = api_key or "mock_api_key"
        self.secret_key = secret_key or "mock_secret_key"
```

## 📍 账户余额相关代码位置

### 1. 获取余额接口

**文件**: `api/roostoo_client.py`

**位置**: 第 217-222 行

```python
def get_balance(self, timeout: Optional[float] = None) -> Dict:
    """[RCL_TopLevelCheck] 获取账户余额信息"""
    headers, _ = self._sign_request({})
    # 对于GET请求，timestamp需要作为URL参数
    params = {'timestamp': headers.pop('timestamp', self._get_timestamp())}
    return self._request('GET', '/v3/balance', headers=headers, params={'timestamp': self._get_timestamp()}, timeout=timeout)
```

### 2. 签名请求方法

**文件**: `api/roostoo_client.py`

**位置**: 第 67-100 行

```python
def _sign_request(self, payload: Dict[str, Any]) -> Tuple[Dict[str, str], str]:
    """为RCL_TopLevelCheck请求生成签名和头部"""
    # 1. 添加时间戳
    payload['timestamp'] = self._get_timestamp()
    
    # 2. 按照key的字母顺序排序参数
    sorted_payload = sorted(payload.items())
    
    # 3. 拼接成 "key1=value1&key2=value2" 格式的字符串
    total_params = urlencode(sorted_payload)
    
    # 4. 使用HMAC-SHA256算法生成签名
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
        
        # 检查余额是否有变化
        balance_changed = True
        if self._last_balance and "total_balance" in self._last_balance:
            if "total_balance" in formatted_balance:
                balance_changed = abs(
                    self._last_balance["total_balance"] - formatted_balance["total_balance"]
                ) > 0.01
        
        if balance_changed:
            self._last_balance = formatted_balance
            # 发布余额数据
            self.bus.publish(self.market_topic, formatted_balance)
            print(f"[MarketDataCollector] Published balance: ${formatted_balance.get('total_balance', 'N/A')}")
            
    except Exception as e:
        print(f"[MarketDataCollector] Error fetching balance: {e}")
```

### 4. 余额数据格式化

**文件**: `api/agents/data_formatter.py`

**位置**: 第 128 行开始

```python
@staticmethod
def format_balance(raw_balance: Dict[str, Any]) -> Dict[str, Any]:
    """格式化余额数据"""
    # 格式化逻辑...
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
    # 提取账户信息
    balance = market_snapshot.get("balance")
    account_equity = str(balance.get("total_balance", "0")) if balance else "0"
    available_cash = str(balance.get("available_balance", "0")) if balance else "0"
    # ...
```

## 🔧 测试步骤

### 1. 验证修复

```bash
# 运行诊断脚本
python diagnose_roostoo_connection.py
```

### 2. 测试余额接口

```python
from api.roostoo_client import RoostooClient

# 创建客户端（会自动使用.env中的真实凭证）
client = RoostooClient()

# 测试获取余额
try:
    balance = client.get_balance(timeout=30.0)
    print(f"✓ 余额获取成功: {balance}")
except Exception as e:
    print(f"✗ 余额获取失败: {e}")
```

### 3. 运行完整测试

```bash
python test_complete_system.py --quick
```

## 📋 配置要求

### Mock API + 真实凭证（推荐用于测试）

```env
# 配置真实的API凭证（即使在Mock API模式下也需要）
ROOSTOO_API_KEY=你的真实API密钥
ROOSTOO_SECRET_KEY=你的真实Secret密钥
ROOSTOO_API_URL=https://mock-api.roostoo.com
```

### Mock API + 测试凭证（仅公开接口）

```env
# 不配置API凭证，或配置测试凭证
# ROOSTOO_API_KEY=
# ROOSTOO_SECRET_KEY=
ROOSTOO_API_URL=https://mock-api.roostoo.com
```

**注意**: 使用测试凭证时，余额接口等需要认证的接口将无法使用。

## 🎯 关键点

1. **Mock API 也需要真实凭证**: Mock API 的余额接口需要有效的 API 凭证才能工作
2. **自动检测凭证**: 代码会自动检测是否提供了真实的 API 凭证
3. **灵活配置**: 可以根据需要选择使用真实凭证或测试凭证

## 🎉 完成

现在余额接口应该可以正常工作了！

**测试**:
```bash
python diagnose_roostoo_connection.py
```

预期输出:
```
✓ 通过: Roostoo客户端
[3.5] 测试余额接口...
   ✓ 余额获取成功
```

