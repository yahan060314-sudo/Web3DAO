# 账户余额API错误分析

## 🚨 错误信息

```
[RoostooClient] ✗ HTTP错误: 401 - Unauthorized
    URL: https://mock-api.roostoo.com/v3/balance?timestamp=1762845484082
    响应内容: api-key invalid
```

## 🔍 问题定位

### 错误位置

**文件**: `api/roostoo_client.py`  
**方法**: `get_balance()` (第209-214行)

### 问题代码

```python
def get_balance(self, timeout: Optional[float] = None) -> Dict:
    """[RCL_TopLevelCheck] 获取账户余额信息"""
    headers, _ = self._sign_request({})
    # 对于GET请求，timestamp需要作为URL参数
    params = {'timestamp': headers.pop('timestamp', self._get_timestamp())} # ❌ 问题1
    return self._request('GET', '/v3/balance', headers=headers, params={'timestamp': self._get_timestamp()}, timeout=timeout)  # ❌ 问题2
```

## 🐛 Bug分析

### Bug 1: headers中没有timestamp键

**问题**:
- `_sign_request()`返回的`headers`只包含`'RST-API-KEY'`和`'MSG-SIGNATURE'`
- `headers`中**没有**`'timestamp'`键
- `headers.pop('timestamp', ...)`会返回默认值（新的时间戳）

**代码位置**: `api/roostoo_client.py` 第87-90行
```python
headers = {
    'RST-API-KEY': self.api_key,
    'MSG-SIGNATURE': signature
}
# 注意：headers中没有timestamp！
```

### Bug 2: 时间戳不一致

**问题**:
- 签名时使用的时间戳：`timestamp1 = self._get_timestamp()` (在`_sign_request()`中)
- 请求时使用的时间戳：`timestamp2 = self._get_timestamp()` (在`get_balance()`第214行)
- **两个时间戳不同**，导致签名验证失败

**时间线**:
```
1. _sign_request({}) 被调用
   └─> timestamp1 = 1762845484082 (用于签名)
   └─> 签名基于: "timestamp=1762845484082"

2. get_balance() 继续执行
   └─> timestamp2 = 1762845484083 (新生成，用于请求)
   └─> 请求URL: /v3/balance?timestamp=1762845484083

3. 服务器验证签名
   └─> 期望签名基于: timestamp=1762845484083
   └─> 实际签名基于: timestamp=1762845484082
   └─> ❌ 签名不匹配 → 401 Unauthorized
```

## ✅ 解决方案

### 方案1: 修改`_sign_request()`返回时间戳

**修改`_sign_request()`方法**，让它返回时间戳：

```python
def _sign_request(self, payload: Dict[str, Any]) -> Tuple[Dict[str, str], str, str]:
    """
    返回: (headers, data_string, timestamp)
    """
    # 1. 添加时间戳
    timestamp = self._get_timestamp()
    payload['timestamp'] = timestamp
    
    # ... 签名逻辑 ...
    
    headers = {
        'RST-API-KEY': self.api_key,
        'MSG-SIGNATURE': signature
    }
    
    return headers, total_params, timestamp  # 返回时间戳
```

**修改`get_balance()`方法**：

```python
def get_balance(self, timeout: Optional[float] = None) -> Dict:
    """[RCL_TopLevelCheck] 获取账户余额信息"""
    headers, _, timestamp = self._sign_request({})  # 获取时间戳
    # 对于GET请求，timestamp需要作为URL参数
    params = {'timestamp': timestamp}  # 使用签名时的时间戳
    return self._request('GET', '/v3/balance', headers=headers, params=params, timeout=timeout)
```

### 方案2: 在`get_balance()`中先获取时间戳（推荐）

**不修改`_sign_request()`**，在`get_balance()`中先获取时间戳：

```python
def get_balance(self, timeout: Optional[float] = None) -> Dict:
    """[RCL_TopLevelCheck] 获取账户余额信息"""
    # 先获取时间戳
    timestamp = self._get_timestamp()
    
    # 使用相同的时间戳进行签名
    payload = {'timestamp': timestamp}
    sorted_payload = sorted(payload.items())
    total_params = urlencode(sorted_payload)
    signature = hmac.new(
        self.secret_key.encode('utf-8'),
        total_params.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        'RST-API-KEY': self.api_key,
        'MSG-SIGNATURE': signature
    }
    
    # 使用相同的时间戳作为URL参数
    params = {'timestamp': timestamp}
    return self._request('GET', '/v3/balance', headers=headers, params=params, timeout=timeout)
```

### 方案3: 修改`_sign_request()`支持返回时间戳（最佳）

**修改`_sign_request()`**，让它返回时间戳，但保持向后兼容：

```python
def _sign_request(self, payload: Dict[str, Any]) -> Tuple[Dict[str, str], str, str]:
    """
    为RCL_TopLevelCheck请求生成签名和头部。
    
    Returns:
        Tuple[Dict[str, str], str, str]: (请求头, 参数字符串, 时间戳)
    """
    # 1. 添加时间戳
    timestamp = self._get_timestamp()
    payload['timestamp'] = timestamp
    
    # ... 签名逻辑 ...
    
    headers = {
        'RST-API-KEY': self.api_key,
        'MSG-SIGNATURE': signature
    }
    
    return headers, total_params, timestamp  # 返回时间戳
```

**修改所有调用`_sign_request()`的地方**：
- `get_balance()`: 使用返回的时间戳
- `get_pending_count()`: 使用返回的时间戳
- `place_order()`: 不需要时间戳（POST请求）
- `query_order()`: 不需要时间戳（POST请求）
- `cancel_order()`: 不需要时间戳（POST请求）

## 📊 影响范围

### 受影响的API方法

1. ✅ `get_balance()` - **有bug**（GET请求，需要时间戳）
2. ✅ `get_pending_count()` - **可能有相同bug**（GET请求，需要时间戳）

### 不受影响的方法

- `place_order()` - POST请求，时间戳在data中
- `query_order()` - POST请求，时间戳在data中
- `cancel_order()` - POST请求，时间戳在data中
- `get_ticker()` - 使用`RCL_TSCheck`，不需要签名
- `check_server_time()` - 不需要认证
- `get_exchange_info()` - 不需要认证

## 🔧 修复步骤

1. **修改`_sign_request()`方法**，返回时间戳
2. **修改`get_balance()`方法**，使用返回的时间戳
3. **修改`get_pending_count()`方法**，使用返回的时间戳
4. **测试修复**，确保401错误消失

## 🧪 测试验证

修复后，运行以下测试：

```bash
python test_complete_flow.py
```

**预期结果**:
- ✅ `get_balance()`调用成功
- ✅ 不再出现401错误
- ✅ 能够获取账户余额数据

