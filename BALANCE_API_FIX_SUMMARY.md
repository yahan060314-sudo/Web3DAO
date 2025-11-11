# 账户余额API错误修复总结

## 🐛 问题描述

在运行`test_complete_flow.py`时，出现401 Unauthorized错误：

```
[RoostooClient] ✗ HTTP错误: 401 - Unauthorized
    URL: https://mock-api.roostoo.com/v3/balance?timestamp=1762845484082
    响应内容: api-key invalid
```

## 🔍 根本原因

**Bug位置**: `api/roostoo_client.py` 的 `get_balance()` 方法

**问题**:
1. `_sign_request()`生成签名时使用时间戳`timestamp1`
2. `get_balance()`请求时使用新的时间戳`timestamp2`
3. 两个时间戳不一致，导致签名验证失败

**错误代码**:
```python
def get_balance(self, timeout: Optional[float] = None) -> Dict:
    headers, _ = self._sign_request({})  # 签名使用timestamp1
    params = {'timestamp': self._get_timestamp()}  # 请求使用timestamp2 ❌
    return self._request('GET', '/v3/balance', headers=headers, params=params, timeout=timeout)
```

## ✅ 修复方案

### 1. 修改`_sign_request()`方法

**修改前**:
```python
def _sign_request(self, payload: Dict[str, Any]) -> Tuple[Dict[str, str], str]:
    # ...
    return headers, total_params
```

**修改后**:
```python
def _sign_request(self, payload: Dict[str, Any]) -> Tuple[Dict[str, str], str, str]:
    # ...
    return headers, total_params, timestamp  # 返回时间戳
```

### 2. 修改`get_balance()`方法

**修改前**:
```python
def get_balance(self, timeout: Optional[float] = None) -> Dict:
    headers, _ = self._sign_request({})
    params = {'timestamp': headers.pop('timestamp', self._get_timestamp())}  # ❌
    return self._request('GET', '/v3/balance', headers=headers, params={'timestamp': self._get_timestamp()}, timeout=timeout)  # ❌
```

**修改后**:
```python
def get_balance(self, timeout: Optional[float] = None) -> Dict:
    headers, _, timestamp = self._sign_request({})  # ✅ 获取时间戳
    params = {'timestamp': timestamp}  # ✅ 使用签名时的时间戳
    return self._request('GET', '/v3/balance', headers=headers, params=params, timeout=timeout)
```

### 3. 修改`get_pending_count()`方法（相同问题）

**修改前**:
```python
def get_pending_count(self) -> Dict:
    headers, _ = self._sign_request({})
    return self._request('GET', '/v3/pending_count', headers=headers, params={'timestamp': self._get_timestamp()})  # ❌
```

**修改后**:
```python
def get_pending_count(self, timeout: Optional[float] = None) -> Dict:
    headers, _, timestamp = self._sign_request({})  # ✅ 获取时间戳
    params = {'timestamp': timestamp}  # ✅ 使用签名时的时间戳
    return self._request('GET', '/v3/pending_count', headers=headers, params=params, timeout=timeout)
```

### 4. 修改POST请求方法（保持兼容）

POST请求方法（`place_order()`, `query_order()`, `cancel_order()`）也使用`_sign_request()`，但它们不需要时间戳（时间戳已在data_string中），所以只需忽略返回的时间戳：

**修改**:
```python
headers, data_string, _ = self._sign_request(payload)  # 忽略时间戳
```

## 📊 修改的文件

**文件**: `api/roostoo_client.py`

**修改的方法**:
1. ✅ `_sign_request()` - 返回时间戳
2. ✅ `get_balance()` - 使用返回的时间戳
3. ✅ `get_pending_count()` - 使用返回的时间戳
4. ✅ `place_order()` - 忽略返回的时间戳
5. ✅ `query_order()` - 忽略返回的时间戳
6. ✅ `cancel_order()` - 忽略返回的时间戳

## 🧪 测试验证

修复后，运行测试：

```bash
python test_complete_flow.py
```

**预期结果**:
- ✅ `get_balance()`调用成功
- ✅ 不再出现401错误
- ✅ 能够获取账户余额数据
- ✅ `MarketDataCollector`能够正常采集余额数据

## 📝 技术细节

### 为什么会出现这个问题？

1. **GET请求的特殊性**: GET请求需要将时间戳作为URL参数，而不是请求体
2. **签名验证**: 服务器验证签名时，会检查URL参数中的时间戳是否与签名时使用的时间戳一致
3. **时间戳不一致**: 如果签名时使用`timestamp1`，但请求时使用`timestamp2`，签名验证会失败

### 为什么其他API调用成功？

- `check_server_time()` - 不需要认证
- `get_exchange_info()` - 不需要认证
- `get_ticker()` - 使用`RCL_TSCheck`，只需要时间戳，不需要签名
- `place_order()` - POST请求，时间戳在请求体中，签名和请求使用相同的时间戳

## ✅ 修复完成

所有相关方法已修复，现在：
- ✅ 签名时使用的时间戳和请求时使用的时间戳一致
- ✅ GET请求正确传递时间戳参数
- ✅ POST请求不受影响（时间戳在请求体中）

