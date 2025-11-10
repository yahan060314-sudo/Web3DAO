# 测试指南：把决策传给市场

## 📋 测试前准备

### 1. 检查环境配置

首先，确保你的 `.env` 文件中有以下配置：

```env
# LLM 配置（至少一个）
DEEPSEEK_API_KEY=sk-your-key-here
# 或
QWEN_API_KEY=your-qwen-key-here
# 或
MINIMAX_API_KEY=your-minimax-key-here

# Roostoo API 配置（测试用，可以使用模拟值）
ROOSTOO_API_KEY=your_roostoo_api_key
ROOSTOO_SECRET_KEY=your_roostoo_secret_key

# Roostoo API URL（重要！）
# 测试环境：使用模拟API（默认）
ROOSTOO_API_URL=https://mock-api.roostoo.com

# 生产环境：使用真实API（需要你提供）
# ROOSTOO_API_URL=https://api.roostoo.com
```

### 2. 安装依赖

```bash
pip install requests python-dotenv
```

---

## 🧪 测试场景

### 场景1: 测试模式（dry_run=True）- 推荐开始

**特点**：
- ✅ 不会真正调用API
- ✅ 只打印下单参数
- ✅ 安全，适合开发测试
- ✅ 不需要真实的API凭证

**测试指令**：

```bash
# 测试增强版执行器（dry_run模式）
python -m api.agents.enhanced_example
```

**预期输出**：
```
[EnhancedExecutor] ⚠️ 测试模式（dry_run=True）
[EnhancedExecutor] ✓ 决策管理器已启用: decisions.db
[EnhancedExecutor] 执行决策:
  Side: BUY
  Pair: BTC/USD
  Quantity: 0.01
  Price: MARKET
  Order Type: MARKET
[EnhancedExecutor] [DRY RUN] 模拟下单:
  - pair: BTC/USD
  - side: BUY
  - quantity: 0.01
  - price: MARKET
[EnhancedExecutor] [DRY RUN] Order NOT placed (dry_run=True)
```

---

### 场景2: 测试 Roostoo API 连接

**特点**：
- ✅ 测试API连接是否正常
- ✅ 验证API凭证是否正确
- ✅ 不会真正下单

**测试指令**：

```bash
# 测试 Roostoo API 连接
python -c "
from api.roostoo_client import RoostooClient
client = RoostooClient()
print(f'API URL: {client.base_url}')
print(f'API Key: {client.api_key[:10]}...' if client.api_key else 'API Key: Not set')
try:
    server_time = client.check_server_time()
    print(f'✓ API连接成功: {server_time}')
except Exception as e:
    print(f'✗ API连接失败: {e}')
"
```

**预期输出**：
```
[RoostooClient] ⚠️ 使用模拟API: https://mock-api.roostoo.com
API URL: https://mock-api.roostoo.com
API Key: your_roos...
✓ API连接成功: {'server_time': 1234567890123}
```

---

### 场景3: 测试完整系统（dry_run模式）

**特点**：
- ✅ 测试完整的决策流程
- ✅ 从AI生成决策到执行器处理
- ✅ 不会真正下单

**测试指令**：

```bash
# 测试完整系统
python test_complete_system.py --quick
```

**预期输出**：
```
✓ Python version: 3.11.x
✓ requests installed
✓ .env file exists
✓ DEEPSEEK_API_KEY configured
...
测试完成！
```

---

### 场景4: 测试真实API（需要真实API URL）

**特点**：
- ⚠️ 需要真实的API URL和凭证
- ⚠️ 可能会真正下单（如果dry_run=False）
- ✅ 测试真实环境

**测试步骤**：

1. **配置真实API URL**：

在 `.env` 文件中设置：
```env
ROOSTOO_API_URL=https://api.roostoo.com  # 替换为真实URL
ROOSTOO_API_KEY=your_real_api_key
ROOSTOO_SECRET_KEY=your_real_secret_key
```

2. **测试连接**：

```bash
python -c "
from api.roostoo_client import RoostooClient
client = RoostooClient()
print(f'API URL: {client.base_url}')
try:
    server_time = client.check_server_time()
    print(f'✓ 真实API连接成功: {server_time}')
except Exception as e:
    print(f'✗ 真实API连接失败: {e}')
"
```

3. **测试获取余额**（不会下单）：

```bash
python -c "
from api.roostoo_client import RoostooClient
client = RoostooClient()
try:
    balance = client.get_balance()
    print(f'✓ 获取余额成功: {balance}')
except Exception as e:
    print(f'✗ 获取余额失败: {e}')
"
```

4. **测试下单（dry_run模式）**：

```bash
python -m api.agents.enhanced_example
# 确保 enhanced_example.py 中 dry_run=True
```

---

## 🚀 快速测试指令

### 1. 最简单的测试（dry_run模式）

```bash
# 测试增强版执行器
python -m api.agents.enhanced_example
```

### 2. 测试API连接

```bash
# 测试Roostoo API连接
python -c "from api.roostoo_client import RoostooClient; client = RoostooClient(); print(f'API URL: {client.base_url}'); print('Connection test:', client.check_server_time())"
```

### 3. 测试完整系统

```bash
# 快速测试
python test_complete_system.py --quick

# 完整测试
python test_complete_system.py --full
```

### 4. 测试多AI综合

```bash
# 测试多AI决策综合
python -m api.llm_clients.multi_llm_example
```

---

## 📝 需要提供的信息

### 1. Roostoo API URL（最重要）

**问题**：真实的Roostoo API URL是什么？

**当前状态**：
- 默认使用：`https://mock-api.roostoo.com`（模拟API）
- 真实API：需要你提供

**如何获取**：
1. 查看Roostoo官方API文档
2. 联系Roostoo技术支持
3. 检查Roostoo平台设置中的API信息

**提供方式**：
- 在 `.env` 文件中设置 `ROOSTOO_API_URL=https://api.roostoo.com`
- 或告诉我真实的URL，我可以帮你配置

### 2. API 凭证

**问题**：你有Roostoo API Key和Secret Key吗？

**当前状态**：
- 测试环境：可以使用模拟值
- 生产环境：需要真实的API凭证

**如何获取**：
1. 登录Roostoo平台
2. 进入API设置页面
3. 创建API Key和Secret Key

**提供方式**：
- 在 `.env` 文件中设置：
  ```env
  ROOSTOO_API_KEY=your_api_key
  ROOSTOO_SECRET_KEY=your_secret_key
  ```

### 3. API 文档

**问题**：你有Roostoo API的详细文档吗？

**需要的信息**：
- API端点列表
- 认证方式
- 请求格式
- 响应格式
- 错误处理

**如果有文档**：
- 可以分享给我，我可以帮你验证代码实现是否正确

---

## 🔧 测试脚本

### 创建测试脚本

创建一个简单的测试脚本 `test_decision_to_market.py`：

```python
#!/usr/bin/env python3
"""
测试"把决策传给市场"功能
"""
import time
from api.agents.bus import MessageBus
from api.agents.enhanced_executor import EnhancedTradeExecutor

def test_dry_run():
    """测试dry_run模式（不会真正下单）"""
    print("=" * 80)
    print("测试1: dry_run模式（不会真正下单）")
    print("=" * 80)
    
    bus = MessageBus()
    executor = EnhancedTradeExecutor(
        bus=bus,
        decision_topic="decisions",
        default_pair="BTC/USD",
        dry_run=True,  # 测试模式，不会真正下单
        enable_decision_manager=True,
        db_path="test_decisions.db"
    )
    
    executor.start()
    print("✓ 执行器已启动（dry_run模式）")
    
    # 模拟决策
    decision = {
        "agent": "test_agent",
        "decision": '{"action": "buy", "quantity": 0.01, "symbol": "BTCUSDT"}',
        "market_snapshot": {
            "ticker": {"price": 50000.0},
            "balance": {}
        },
        "timestamp": time.time(),
        "json_valid": True
    }
    
    bus.publish("decisions", decision)
    print("✓ 决策已发布")
    
    time.sleep(2)
    
    stats = executor.get_statistics()
    print(f"✓ 统计信息: {stats}")
    
    executor.stop()
    print("✓ 测试完成")

def test_api_connection():
    """测试API连接"""
    print("=" * 80)
    print("测试2: API连接测试")
    print("=" * 80)
    
    from api.roostoo_client import RoostooClient
    
    try:
        client = RoostooClient()
        print(f"✓ API URL: {client.base_url}")
        print(f"✓ API Key: {client.api_key[:10]}..." if client.api_key else "✗ API Key: Not set")
        
        server_time = client.check_server_time()
        print(f"✓ API连接成功: {server_time}")
        
        return True
    except Exception as e:
        print(f"✗ API连接失败: {e}")
        return False

if __name__ == "__main__":
    # 测试1: dry_run模式
    test_dry_run()
    
    print("\n")
    
    # 测试2: API连接
    test_api_connection()
```

**运行方式**：

```bash
python test_decision_to_market.py
```

---

## ✅ 测试检查清单

### 测试前检查

- [ ] ✅ `.env` 文件已创建
- [ ] ✅ LLM API Key已配置（至少一个）
- [ ] ✅ Roostoo API Key已配置（可以使用模拟值）
- [ ] ✅ Roostoo Secret Key已配置（可以使用模拟值）
- [ ] ✅ Roostoo API URL已配置（测试环境使用mock API）
- [ ] ✅ 依赖已安装（requests, python-dotenv）

### 测试步骤

1. [ ] ✅ 测试dry_run模式（不会真正下单）
2. [ ] ✅ 测试API连接
3. [ ] ✅ 测试完整系统
4. [ ] ✅ 测试决策管理器
5. [ ] ✅ 测试多AI综合（可选）

### 生产环境检查

- [ ] ✅ 真实的Roostoo API URL已配置
- [ ] ✅ 真实的API Key和Secret Key已配置
- [ ] ✅ API连接测试成功
- [ ] ✅ 获取余额测试成功
- [ ] ✅ 限频设置正确
- [ ] ✅ 风险控制已设置

---

## 🐛 常见问题

### Q1: 测试时出现 "API Key not set" 错误

**解决**：
1. 检查 `.env` 文件是否存在
2. 检查 `ROOSTOO_API_KEY` 和 `ROOSTOO_SECRET_KEY` 是否配置
3. 检查 `.env` 文件格式是否正确（不要有多余的空格或引号）

### Q2: 测试时出现 "API连接失败" 错误

**解决**：
1. 检查网络连接
2. 检查API URL是否正确
3. 检查API Key和Secret Key是否正确
4. 如果使用mock API，确保mock API服务正常

### Q3: 测试时没有看到下单信息

**解决**：
1. 检查 `dry_run` 参数是否正确设置
2. 检查决策是否正确发布到消息总线
3. 检查执行器是否正常启动
4. 查看日志输出

### Q4: 如何测试真实API？

**解决**：
1. 获取真实的Roostoo API URL
2. 获取真实的API Key和Secret Key
3. 在 `.env` 文件中配置
4. 先测试API连接，再测试下单（使用dry_run模式）

---

## 📞 需要帮助？

如果你在测试过程中遇到问题，请告诉我：

1. **错误信息**：完整的错误信息
2. **测试场景**：你在测试哪个场景？
3. **配置信息**：你的 `.env` 文件配置（隐藏敏感信息）
4. **API信息**：如果你有真实的Roostoo API URL和文档，可以分享给我

---

## 🎯 总结

### 测试步骤

1. **开始测试**：使用dry_run模式（不会真正下单）
   ```bash
   python -m api.agents.enhanced_example
   ```

2. **测试API连接**：
   ```bash
   python -c "from api.roostoo_client import RoostooClient; client = RoostooClient(); print(client.check_server_time())"
   ```

3. **测试完整系统**：
   ```bash
   python test_complete_system.py --quick
   ```

### 需要提供的信息

1. **Roostoo API URL**：真实的API URL是什么？
2. **API凭证**：你有API Key和Secret Key吗？
3. **API文档**：你有Roostoo API的详细文档吗？

### 下一步

1. 运行测试脚本，查看结果
2. 如果测试成功，可以尝试配置真实API
3. 如果测试失败，查看错误信息，我可以帮你解决

