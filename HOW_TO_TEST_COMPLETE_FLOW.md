# 如何测试完整流程

## 🎯 测试目标

测试从市场数据获取 → AI决策生成 → 交易执行的完整流程，确保系统能够正常运行。

## 📋 测试前准备

### 1. 配置环境变量

确保 `.env` 文件包含以下配置：

```env
# Roostoo API（必须）
ROOSTOO_API_KEY=你的API密钥
ROOSTOO_SECRET_KEY=你的Secret密钥
ROOSTOO_API_URL=https://api.roostoo.com

# LLM API（至少配置一个）
DEEPSEEK_API_KEY=你的DeepSeek API密钥
# 或
QWEN_API_KEY=你的Qwen API密钥
# 或
MINIMAX_API_KEY=你的Minimax API密钥

# LLM提供商（默认: deepseek）
LLM_PROVIDER=deepseek
```

### 2. 安装依赖

```bash
pip install requests python-dotenv
```

## 🚀 测试方法

### 方法1: 运行完整流程测试（推荐）

```bash
python test_complete_flow.py
```

**这个脚本会测试**:
1. ✅ Roostoo API 连接
2. ✅ LLM 连接（DeepSeek/Qwen/Minimax）
3. ✅ 市场数据采集
4. ✅ AI决策生成
5. ✅ 决策执行（dry_run模式，不会真正下单）
6. ✅ 完整流程（端到端）

**预计时间**: 2-3分钟

### 方法2: 运行现有测试脚本

```bash
# 快速测试（约30秒）
python test_complete_system.py --quick

# 完整测试（约2分钟）
python test_complete_system.py --full
```

### 方法3: 运行集成示例

```bash
# 运行集成示例（会运行约1分钟）
python -m api.agents.example_run
```

## 📝 分步测试

### 步骤1: 测试 Roostoo API 连接

```bash
python test_real_api.py
```

**预期输出**:
```
✓ 服务器时间获取成功
✓ 交易所信息获取成功
✓ 市场数据获取成功
```

### 步骤2: 测试 LLM 连接

```bash
python -m api.llm_clients.example_usage
```

**预期输出**:
```
✓ 成功初始化 deepseek 客户端
✓ LLM响应: ...
```

### 步骤3: 测试市场数据采集

```bash
python -c "
import time
from api.agents.bus import MessageBus
from api.agents.market_collector import MarketDataCollector

bus = MessageBus()
collector = MarketDataCollector(
    bus=bus,
    market_topic='market_ticks',
    pairs=['BTC/USD'],
    collect_interval=5.0
)

collector.start()
time.sleep(6)
collector.stop()
"
```

### 步骤4: 测试 AI决策生成

```bash
python -c "
import time
from api.agents.manager import AgentManager

mgr = AgentManager()
mgr.add_agent(name='TestAgent', system_prompt='You are a trading assistant.')
mgr.start()

mgr.broadcast_prompt(role='user', content='Analyze BTC market and make a decision.')
time.sleep(10)

decisions = mgr.collect_decisions(max_items=5, wait_seconds=2.0)
print(f'Received {len(decisions)} decisions')
mgr.stop()
"
```

### 步骤5: 测试决策执行（dry_run模式）

```bash
python test_decision_to_market.py
```

**预期输出**:
```
✓ 决策解析成功
✓ 执行参数: ...
✓ 测试模式: dry_run（不会真正下单）
```

### 步骤6: 测试完整流程

```bash
python test_complete_flow.py
```

## ✅ 测试通过标准

如果看到以下输出，说明测试通过：

```
================================================================================
测试结果总结
================================================================================
✓ 通过: 步骤1: Roostoo API
✓ 通过: 步骤2: LLM 连接
✓ 通过: 步骤3: 市场数据采集
✓ 通过: 步骤4: AI决策生成
✓ 通过: 步骤5: 决策执行
✓ 通过: 步骤6: 完整流程
```

## 🐛 常见问题

### 问题1: API 连接失败

**错误**: `API Key和Secret Key不能为空`

**解决方法**:
1. 检查 `.env` 文件是否存在
2. 检查 API 凭证是否正确配置
3. 检查环境变量是否正确加载

### 问题2: LLM 连接失败

**错误**: `DEEPSEEK_API_KEY not set`

**解决方法**:
1. 检查 `.env` 文件中的 LLM API Key
2. 检查 `LLM_PROVIDER` 设置
3. 确认 API Key 是否有效

### 问题3: 市场数据采集失败

**错误**: `Error fetching ticker` 或 `Error fetching balance`

**解决方法**:
1. 检查 Roostoo API 连接
2. 检查交易对名称是否正确
3. 检查 API 权限（余额查询可能需要特殊权限）
4. 如果使用真实API，确保比赛已开始

### 问题4: AI决策生成失败

**错误**: `No decisions received` 或 `LLM timeout`

**解决方法**:
1. 检查 LLM API 连接
2. 增加等待时间
3. 检查网络连接
4. 检查 API 配额

### 问题5: 决策执行失败

**错误**: `Decision cannot be parsed` 或 `Execution failed`

**解决方法**:
1. 检查决策格式（JSON 或自然语言）
2. 检查决策解析逻辑
3. 检查 dry_run 模式设置
4. 查看日志输出

## 📊 测试输出示例

### 成功输出

```
================================================================================
完整流程测试
================================================================================

检查环境变量...
✓ .env 文件存在
✓ ROOSTOO_API_KEY 已配置
✓ ROOSTOO_SECRET_KEY 已配置
✓ LLM_PROVIDER: deepseek

================================================================================
测试步骤1: Roostoo API 连接
================================================================================
✓ RoostooClient 创建成功
  API URL: https://api.roostoo.com
  API Key: K9IL3ZxCV1...

1. 测试服务器时间...
   ✓ 服务器时间: {'ServerTime': ...}

2. 测试获取交易所信息...
   ✓ 交易所信息获取成功

3. 测试获取市场数据 (BTC/USD)...
   ✓ 市场数据获取成功

✓ 步骤1完成: Roostoo API 连接测试

...

================================================================================
测试结果总结
================================================================================
✓ 通过: 步骤1: Roostoo API
✓ 通过: 步骤2: LLM 连接
✓ 通过: 步骤3: 市场数据采集
✓ 通过: 步骤4: AI决策生成
✓ 通过: 步骤5: 决策执行
✓ 通过: 步骤6: 完整流程
```

## 🎉 测试通过后

如果所有测试都通过，你可以：

1. **继续开发**: 在 main 分支上继续开发
2. **部署到生产**: 配置真实的 API URL 和凭证
3. **运行真实交易**: 设置 `dry_run=False` 进行真实交易（谨慎！）

## 📚 相关文档

- [COMPLETE_FLOW_TEST_GUIDE.md](./COMPLETE_FLOW_TEST_GUIDE.md) - 详细测试指南
- [QUICK_TEST.md](./QUICK_TEST.md) - 快速测试指南
- [TESTING_GUIDE_DECISION_TO_MARKET.md](./TESTING_GUIDE_DECISION_TO_MARKET.md) - 决策到市场测试指南
- [SETUP_REAL_API.md](./SETUP_REAL_API.md) - 真实API设置指南

## 🔍 测试检查清单

### 测试前检查

- [ ] ✅ `.env` 文件已创建并配置
- [ ] ✅ `ROOSTOO_API_KEY` 已配置
- [ ] ✅ `ROOSTOO_SECRET_KEY` 已配置
- [ ] ✅ `ROOSTOO_API_URL` 已配置（真实或模拟）
- [ ] ✅ `DEEPSEEK_API_KEY` 或 `QWEN_API_KEY` 已配置
- [ ] ✅ 依赖已安装（requests, python-dotenv）

### 测试步骤检查

- [ ] ✅ 步骤1: Roostoo API 连接测试通过
- [ ] ✅ 步骤2: LLM 连接测试通过
- [ ] ✅ 步骤3: 市场数据采集测试通过
- [ ] ✅ 步骤4: AI决策生成测试通过
- [ ] ✅ 步骤5: 决策执行测试通过
- [ ] ✅ 步骤6: 完整流程测试通过

## 💡 提示

1. **dry_run 模式**: 所有测试都使用 `dry_run=True`，不会真正下单
2. **真实交易**: 如果要进行真实交易，需要设置 `dry_run=False`，并确保API凭证正确
3. **比赛状态**: 如果使用真实API，确保比赛已开始
4. **网络连接**: 确保网络连接正常，能够访问API服务器
5. **API配额**: 检查LLM API的配额，确保有足够的调用次数

