# 账户余额相关代码位置

## 📍 核心代码位置

### 1. 获取余额接口（主要代码）

**文件**: `api/roostoo_client.py`

**位置**: 第 217-222 行

```python
def get_balance(self, timeout: Optional[float] = None) -> Dict:
    """[RCL_TopLevelCheck] 获取账户余额信息"""
    headers, _ = self._sign_request({})
    # 对于GET请求，timestamp需要作为URL参数
    params = {'timestamp': self._get_timestamp()}
    return self._request('GET', '/v3/balance', headers=headers, params=params, timeout=timeout)
```

**功能**: 
- 调用 Roostoo API 的 `/v3/balance` 端点
- 使用 HMAC-SHA256 签名进行认证
- 返回账户余额信息

### 2. 请求签名方法

**文件**: `api/roostoo_client.py`

**位置**: 第 80-100 行

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

**功能**: 
- 为需要认证的API请求生成签名
- 使用 API Key 和 Secret Key 进行HMAC-SHA256签名
- 返回请求头和签名字符串

### 3. 客户端初始化（凭证管理）

**文件**: `api/roostoo_client.py`

**位置**: 第 30-74 行

```python
def __init__(self, api_key: str = API_KEY, secret_key: str = SECRET_KEY, base_url: str = None):
    """初始化客户端"""
    # 支持通过参数或环境变量配置base_url
    self.base_url = base_url or BASE_URL
    
    # 检查是否是Mock API
    is_mock_api = "mock" in self.base_url.lower()
    
    # 检查是否提供了真实的API凭证
    has_real_credentials = (
        api_key and 
        secret_key and 
        api_key.strip() != "" and 
        secret_key.strip() != "" and
        api_key != "mock_api_key" and 
        secret_key != "mock_secret_key"
    )
    
    if is_mock_api:
        if has_real_credentials:
            # 使用真实凭证（即使是在Mock API模式下）
            self.api_key = api_key
            self.secret_key = secret_key
        else:
            # 使用测试凭证
            self.api_key = api_key or "mock_api_key"
            self.secret_key = secret_key or "mock_secret_key"
    else:
        # 真实API必须提供有效的凭证
        if not api_key or not secret_key:
            raise ValueError("API Key和Secret Key不能为空。")
        self.api_key = api_key
        self.secret_key = secret_key
```

**功能**: 
- 初始化 Roostoo 客户端
- 管理 API 凭证（优先使用真实凭证）
- 区分 Mock API 和真实 API 的处理逻辑

## 📍 使用余额的代码位置

### 4. 市场数据采集器

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

**功能**: 
- 定期从 Roostoo API 获取账户余额
- 格式化余额数据
- 发布到消息总线，供其他组件使用

### 5. 余额数据格式化

**文件**: `api/agents/data_formatter.py`

**位置**: 第 128-196 行

```python
@staticmethod
def format_balance(raw_balance: Dict[str, Any]) -> Dict[str, Any]:
    """格式化账户余额数据"""
    formatted = {
        "type": "balance",
        "timestamp": time.time(),
        "raw": raw_balance
    }
    
    # 处理Roostoo的SpotWallet格式
    data = raw_balance.get("data", raw_balance)
    spot_wallet = data.get("SpotWallet", {})
    
    if spot_wallet:
        currencies = {}
        total_balance = 0.0
        available_balance = 0.0
        
        for currency, wallet_info in spot_wallet.items():
            if isinstance(wallet_info, dict):
                free = float(wallet_info.get("Free", 0))
                locked = float(wallet_info.get("Lock", 0))
                total = free + locked
                
                currencies[currency] = {
                    "available": free,
                    "locked": locked,
                    "total": total
                }
                
                total_balance += total
                available_balance += free
        
        formatted["currencies"] = currencies
        formatted["total_balance"] = total_balance
        formatted["available_balance"] = available_balance
    
    return formatted
```

**功能**: 
- 将 Roostoo API 返回的原始余额数据格式化为统一格式
- 提取总余额、可用余额、各币种余额等信息
- 处理不同的数据格式

### 6. Prompt管理器（使用余额）

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
    if balance is None:
        balance = {}
    
    account_equity = str(balance.get("total_balance", "0")) if balance else "0"
    available_cash = str(balance.get("available_balance", "0")) if balance else "0"
    
    # 格式化持仓信息
    positions_parts = []
    if balance and "currencies" in balance:
        currencies = balance.get("currencies", {})
        if isinstance(currencies, dict):
            for currency, amounts in currencies.items():
                if isinstance(amounts, dict):
                    total = amounts.get("total", 0)
                    if total > 0:
                        positions_parts.append(f"{currency}: {total}")
    positions = ", ".join(positions_parts) if positions_parts else "无持仓"
    
    # 使用模板生成prompt
    return self.get_spot_trading_prompt(
        date=date,
        account_equity=account_equity,
        available_cash=available_cash,
        positions=positions,
        ...
    )
```

**功能**: 
- 从市场快照中提取余额信息
- 将余额信息格式化为 AI Agent 可用的 prompt
- 用于生成交易决策

### 7. BaseAgent（使用余额）

**文件**: `api/agents/base_agent.py`

**位置**: 第 89-120 行

```python
def _handle_market_data(self, msg: Dict[str, Any]) -> None:
    """处理接收到的市场数据"""
    data_type = msg.get("type", "unknown")
    
    if data_type == "ticker":
        # 更新ticker数据
        pair = msg.get("pair")
        if pair:
            self.current_tickers[pair] = msg
    elif data_type == "balance":
        # 更新余额数据
        self.current_balance = msg
    
    # 创建综合市场快照
    ticker = None
    if self.current_tickers:
        ticker = list(self.current_tickers.values())[0]
    
    self.last_market_snapshot = self.formatter.create_market_snapshot(
        ticker=ticker,
        balance=self.current_balance
    )
```

**功能**: 
- 接收市场数据（包括余额数据）
- 更新内部状态
- 创建市场快照供决策使用

## 🔧 修复说明

### 问题

余额接口返回 401 错误，提示 "api-key invalid"

### 原因

1. Mock API 模式下，代码自动使用测试凭证
2. 即使 `.env` 文件中配置了真实凭证，也被忽略了
3. Mock API 的余额接口需要有效的 API 凭证

### 解决方案

**修改文件**: `api/roostoo_client.py` 第 45-63 行

**改进**:
- ✅ 检查是否提供了真实的 API 凭证
- ✅ 如果提供了真实凭证，即使在 Mock API 模式下也使用真实凭证
- ✅ 只有在没有提供任何凭证的情况下，才使用测试凭证
- ✅ 更清晰的提示信息

## 📋 配置要求

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

## 🎯 测试方法

### 测试余额接口

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

### 运行测试脚本

```bash
python test_balance_fix.py
```

## 📚 相关文档

- [FIX_BALANCE_401_ERROR.md](./FIX_BALANCE_401_ERROR.md) - 详细修复说明
- [BALANCE_API_FIX.md](./BALANCE_API_FIX.md) - API修复说明
- [ROOSTOO_CONNECTION_SOLUTION.md](./ROOSTOO_CONNECTION_SOLUTION.md) - 连接问题解决方案

