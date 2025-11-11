# "把决策传给市场" 简单解释

## 🎯 一句话解释

**"把决策传给市场" = 你的程序自动调用 Roostoo 交易平台的 API，发送买入/卖出指令**

---

## 📖 详细解释

### 1. "市场"是什么？

**"市场" = Roostoo 交易平台**

- 这是一个**在线的加密货币交易平台**
- 类似于股票交易所，但交易的是加密货币（BTC、ETH等）
- 比赛使用的是**模拟交易环境**（不会用真实资金）

### 2. "传"是怎么实现的？

**"传" = 程序自动发送 HTTP 请求**

就像你打开浏览器访问网页一样，程序会自动发送 HTTP 请求到 Roostoo 平台。

**具体过程**:
```
你的程序 → 构建 HTTP 请求 → 发送到 Roostoo API → Roostoo 执行交易 → 返回结果
```

### 3. 完整的流程

```
步骤1: AI 说 "买入 0.01 个 BTC"
   ↓
步骤2: 程序理解: "要买入 0.01 个 BTC/USD"
   ↓
步骤3: 程序调用: RoostooClient.place_order(pair="BTC/USD", side="BUY", quantity=0.01)
   ↓
步骤4: RoostooClient 构建 HTTP 请求:
   - URL: https://api.roostoo.com/v3/place_order
   - 方法: POST
   - 参数: pair=BTC/USD, side=BUY, quantity=0.01
   - 签名: 使用你的 API Key 和 Secret Key 生成签名
   ↓
步骤5: 发送 HTTP 请求到 Roostoo 平台
   ↓
步骤6: Roostoo 平台收到请求，验证身份，执行交易
   ↓
步骤7: Roostoo 平台返回结果: "订单已成交，订单ID: 12345"
```

---

## 💻 代码示例

### 最简单的例子

```python
from api.roostoo_client import RoostooClient

# 1. 创建 Roostoo 客户端
client = RoostooClient()

# 2. 下单（这就是"传给市场"！）
result = client.place_order(
    pair="BTC/USD",    # 交易对
    side="BUY",        # 买入
    quantity=0.01      # 数量
)

# 3. 查看结果
print(result)  # {"order_id": "12345", "status": "filled", ...}
```

### 在实际系统中的使用

```python
# api/agents/executor.py
class TradeExecutor:
    def _maybe_execute(self, decision_msg):
        # 1. 解析 AI 的决策
        parsed = self._parse_decision(decision_msg)
        # 返回: {"side": "BUY", "quantity": 0.01, "pair": "BTC/USD"}
        
        # 2. 调用 RoostooClient 下单（这就是"传给市场"！）
        resp = self.client.place_order(
            pair=parsed["pair"],
            side=parsed["side"],
            quantity=parsed["quantity"]
        )
        
        # 3. 打印结果
        print(f"订单已提交: {resp}")
```

---

## 🔍 关键点

### 1. 不需要人工操作

- 整个过程是**自动的**
- 不需要你手动打开网页或点击按钮
- 程序会自动执行

### 2. 通过 HTTP API 通信

- 就像你发微信消息一样，程序发送 HTTP 请求
- Roostoo 平台收到请求后，执行交易
- 然后返回结果

### 3. 需要 API 凭证

- 就像登录账号需要密码一样
- 需要 API Key 和 Secret Key 来验证身份
- 这些凭证存储在 `.env` 文件中

---

## 📝 需要的信息

要完成"传给市场"，你需要：

1. **API 凭证**（从 Roostoo 平台获取）:
   - `ROOSTOO_API_KEY`: 你的 API 密钥
   - `ROOSTOO_SECRET_KEY`: 你的 Secret 密钥

2. **API URL**:
   - 测试环境: `https://mock-api.roostoo.com`
   - 生产环境: `https://api.roostoo.com`（需要确认）

3. **配置 .env 文件**:
   ```env
   ROOSTOO_API_KEY=your_api_key
   ROOSTOO_SECRET_KEY=your_secret_key
   ROOSTOO_API_URL=https://api.roostoo.com
   ```

---

## ❓ 常见问题

### Q: 这是真实的交易吗？

**A**: 比赛使用的是**模拟交易环境**，不会用真实资金。但代码逻辑是一样的。

### Q: 需要我手动操作吗？

**A**: 不需要。程序会自动执行所有操作。

### Q: 如果出错了怎么办？

**A**: 程序会记录错误信息，你可以查看日志。如果使用 `EnhancedTradeExecutor`，所有错误都会存储到数据库中。

### Q: 如何测试？

**A**: 
1. 使用 `dry_run=True` 模式（只打印，不下单）
2. 使用模拟 API (`https://mock-api.roostoo.com`)
3. 使用真实 API（需要真实的 API 凭证）

---

## 🎯 总结

**"把决策传给市场"** 就是：
1. AI 生成决策（如 "买入 0.01 BTC"）
2. 程序解析决策
3. 程序调用 `RoostooClient.place_order()`
4. `RoostooClient` 发送 HTTP 请求到 Roostoo API
5. Roostoo 平台执行交易
6. 返回交易结果

**关键代码**: `api/roostoo_client.py` - `place_order()` 方法

**关键文件**: 
- `api/roostoo_client.py` - Roostoo API 客户端
- `api/agents/executor.py` - 交易执行器

---

## 📚 下一步

1. **查看代码**: 打开 `api/roostoo_client.py`，查看 `place_order()` 方法
2. **查看文档**: 阅读 `HOW_DECISION_TO_MARKET_WORKS.md` 了解详细流程
3. **测试**: 运行 `api/agents/enhanced_example.py` 测试功能
4. **配置**: 在 `.env` 文件中配置 API 凭证

