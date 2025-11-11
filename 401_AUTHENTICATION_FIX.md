# 401认证错误修复报告

## 🚨 问题描述

在使用Roostoo API时一直出现401 Unauthorized错误，即使使用的是官方提供的API。

## 🔍 问题分析

通过对比官方文档和代码实现，发现了以下关键问题：

### 问题1: GET请求签名验证失败 ⚠️ **最关键的401错误原因**

**位置**: `api/roostoo_client.py` 的 `get_balance()` 和 `get_pending_count()` 方法

**问题分析**:
根据官方文档：
> totalParams is defined as the query string in GET request OR request body in POST request.

这意味着：
- **POST请求**: 服务器使用请求体（request body）来验证签名
- **GET请求**: 服务器使用查询字符串（query string）来验证签名

**原代码的问题**:
```python
def get_balance(self, timeout: Optional[float] = None) -> Dict:
    headers, _, timestamp = self._sign_request({})  # 生成签名时使用 "timestamp=167..."
    params = {'timestamp': timestamp}  # 创建新的字典
    return self._request('GET', '/v3/balance', headers=headers, params=params, timeout=timeout)
```

**问题**:
1. `_sign_request()` 生成了签名，基于字符串 `"timestamp=167..."`
2. 但代码丢弃了用于签名的 `total_params` 字符串
3. 重新创建了 `params` 字典，让 `requests` 库自动转换为查询字符串
4. `requests` 库生成的查询字符串可能与签名时使用的字符串不完全一致（虽然单个参数可能看起来一样，但为了100%保证一致，必须使用相同的字符串）

**修复方案**:
```python
def get_balance(self, timeout: Optional[float] = None) -> Dict:
    headers, total_params, _ = self._sign_request({})  # 获取用于签名的total_params字符串
    # 直接使用签名时生成的total_params字符串拼接到URL
    return self._request('GET', f'/v3/balance?{total_params}', headers=headers, timeout=timeout)
```

这样确保服务器验证签名时使用的查询字符串和签名时使用的完全一致。

### 问题2: 参数名错误 ⚠️ **关键问题**

**位置**: `api/roostoo_client.py` 的 `place_order()` 方法

**错误代码**:
```python
payload['order_type'] = 'LIMIT'  # ❌ 错误
payload['order_type'] = 'MARKET'  # ❌ 错误
```

**官方文档要求**:
```python
payload['type'] = 'LIMIT'   # ✅ 正确
payload['type'] = 'MARKET'  # ✅ 正确
```

**影响**: 
- 签名时使用了错误的参数名 `order_type`
- 服务器期望的参数名是 `type`
- 导致签名验证失败，返回401错误

### 问题3: 参数拼接方式不一致

**位置**: `api/roostoo_client.py` 的 `_sign_request()` 方法

**原代码**:
```python
total_params = urlencode(sorted_payload)  # 会对特殊字符进行URL编码
```

**官方文档示例**:
```
pair=BNB/USD&quantity=2000&side=BUY&timestamp=1580774512000&type=MARKET
```

**问题**: 
- `urlencode` 会对 `/` 等特殊字符进行编码（如 `BNB/USD` 变成 `BNB%2FUSD`）
- 官方文档示例显示使用原始字符串拼接
- 虽然可能不是主要问题，但为了完全匹配官方文档，应该使用原始拼接

**修复后**:
```python
total_params = "&".join(f"{k}={v}" for k, v in sorted_payload)
```

## ✅ 修复方案

### 修复1: GET请求使用签名时的查询字符串

**文件**: `api/roostoo_client.py`

**修改前**:
```python
def get_balance(self, timeout: Optional[float] = None) -> Dict:
    headers, _, timestamp = self._sign_request({})
    params = {'timestamp': timestamp}
    return self._request('GET', '/v3/balance', headers=headers, params=params, timeout=timeout)
```

**修改后**:
```python
def get_balance(self, timeout: Optional[float] = None) -> Dict:
    headers, total_params, _ = self._sign_request({})
    # 直接使用签名时生成的total_params字符串拼接到URL
    return self._request('GET', f'/v3/balance?{total_params}', headers=headers, timeout=timeout)
```

**同样修复**:
- `get_pending_count()` 方法也进行了相同的修复

### 修复2: 更正参数名

**文件**: `api/roostoo_client.py`

**修改前**:
```python
if price is not None:
    payload['order_type'] = 'LIMIT'
    payload['price'] = str(price)
else:
    payload['order_type'] = 'MARKET'
```

**修改后**:
```python
if price is not None:
    payload['type'] = 'LIMIT'  # 修复：使用 'type' 而不是 'order_type'
    payload['price'] = str(price)
else:
    payload['type'] = 'MARKET'  # 修复：使用 'type' 而不是 'order_type'
```

### 修复3: 使用原始字符串拼接

**文件**: `api/roostoo_client.py`

**修改前**:
```python
from urllib.parse import urlencode
# ...
total_params = urlencode(sorted_payload)
```

**修改后**:
```python
# 移除 urlencode 导入
# ...
# 使用原始字符串拼接，匹配官方文档示例
total_params = "&".join(f"{k}={v}" for k, v in sorted_payload)
```

## 📋 官方文档关键要求总结

根据官方文档，SIGNED端点需要：

1. **参数排序**: 按照key的字母顺序排序
2. **参数拼接**: `key1=value1&key2=value2` 格式（不使用URL编码）
3. **签名算法**: HMAC SHA256
4. **请求头**:
   - `RST-API-KEY`: API密钥
   - `MSG-SIGNATURE`: HMAC签名
   - `Content-Type`: `application/x-www-form-urlencoded` (POST请求)
5. **时间戳**: 13位毫秒时间戳，必须在服务器时间±60秒内
6. **参数名**: 必须完全匹配官方文档（如 `type` 而不是 `order_type`）
7. **GET请求查询字符串**: **必须使用签名时生成的 `total_params` 字符串作为查询字符串**，确保服务器验证签名时使用的查询字符串和签名时使用的完全一致

## 🧪 验证步骤

修复后，请测试以下功能：

1. **获取余额**:
   ```python
   client = RoostooClient()
   balance = client.get_balance()
   ```

2. **下单**:
   ```python
   # 市价单
   result = client.place_order("BNB/USD", "BUY", 1)
   
   # 限价单
   result = client.place_order("BNB/USD", "BUY", 1, price=300)
   ```

3. **查询订单**:
   ```python
   orders = client.query_order(pair="BNB/USD")
   ```

## 🔑 其他可能的问题

如果修复后仍然出现401错误，请检查：

1. **API密钥和Secret密钥是否正确**:
   - 检查 `.env` 文件中的 `ROOSTOO_API_KEY` 和 `ROOSTOO_SECRET_KEY`
   - 确保没有多余的空格或换行符

2. **时间戳同步**:
   - 确保系统时间准确
   - 服务器会拒绝与服务器时间相差超过60秒的请求

3. **API URL配置**:
   - 确保 `ROOSTOO_API_URL` 设置为 `https://mock-api.roostoo.com`

4. **网络连接**:
   - 确保可以访问API服务器
   - 检查防火墙或代理设置

## 📝 修复文件清单

- ✅ `api/roostoo_client.py` - 修复GET请求签名验证、参数名和参数拼接方式
  - `get_balance()`: 使用签名时的 `total_params` 字符串作为查询字符串
  - `get_pending_count()`: 使用签名时的 `total_params` 字符串作为查询字符串
  - `place_order()`: 修复参数名从 `order_type` 改为 `type`
  - `_sign_request()`: 使用原始字符串拼接而不是 `urlencode`

## 🎯 预期结果

修复后，所有需要认证的API调用应该能够正常工作，不再出现401错误。

