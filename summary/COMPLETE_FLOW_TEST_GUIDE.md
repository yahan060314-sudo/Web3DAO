# 完整流程测试指南

## 🎯 测试目标

测试从市场数据获取 → AI决策生成 → 交易执行的完整流程，确保系统能够正常运行。

## 📋 测试流程

```
1. Roostoo API 连接测试
   ↓
2. LLM 连接测试（DeepSeek/Qwen/Minimax）
   ↓
3. 市场数据采集测试
   ↓
4. AI决策生成测试
   ↓
5. 决策执行测试（dry_run模式）
   ↓
6. 完整流程测试（端到端）
```

## 🚀 快速测试

### 方法1: 运行完整测试脚本（推荐）

```bash
# 运行完整流程测试
python test_complete_flow.py
```

这个脚本会测试所有步骤，包括：
- ✅ Roostoo API 连接
- ✅ LLM 连接
- ✅ 市场数据采集
- ✅ AI决策生成
- ✅ 决策执行（dry_run模式）
- ✅ 完整流程（端到端）

### 方法2: 运行现有测试脚本

```bash
# 运行完整系统测试
python test_complete_system.py --quick
```

### 方法3: 运行集成示例

```bash
# 运行集成示例（会运行2分钟）
python -m api.agents.example_run
```

## 📝 详细测试步骤

### 步骤1: 测试 Roostoo API 连接

```bash
python -c "
from api.roostoo_client import RoostooClient
client = RoostooClient()
print('API URL:', client.base_url)
print('Server time:', client.check_server_time())
"
```

**预期输出**:
```
[RoostooClient] ✓ 使用真实API: https://api.roostoo.com
API URL: https://api.roostoo.com
Server time: {'ServerTime': ...}
```

### 步骤2: 测试 LLM 连接

```bash
python -m api.llm_clients.example_usage
```

**预期输出**:
```
✓ 成功初始化 deepseek 客户端
...
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

### 步骤6: 测试完整流程

```bash
python test_complete_flow.py
```

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

## 🐛 常见问题

### 问题1: Roostoo API 连接失败

**错误**: `Connection failed` 或 `HTTP Error`

**解决方法**:
1. 检查 `.env` 文件中的 `ROOSTOO_API_URL`
2. 检查网络连接
3. 确认比赛是否已开始（如果使用真实API）
4. 检查 API Key 和 Secret Key 是否正确

### 问题2: LLM 连接失败

**错误**: `API key not set` 或 `Authentication failed`

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

================================================================================
测试步骤2: LLM 连接
================================================================================
使用LLM提供商: deepseek
✓ LLM客户端创建成功: DeepSeekClient

测试LLM调用...
   ✓ LLM响应: hello

✓ 步骤2完成: LLM 连接测试

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

## 🎯 测试命令汇总

### 快速测试（推荐）

```bash
# 运行完整流程测试（约2-3分钟）
python test_complete_flow.py
```

### 分步测试

```bash
# 1. 测试 Roostoo API
python test_real_api.py

# 2. 测试决策执行
python test_decision_to_market.py

# 3. 测试完整系统
python test_complete_system.py --quick
```

### 集成测试

```bash
# 运行集成示例
python -m api.agents.example_run
```

## 📝 测试结果解读

### 所有测试通过 ✅

如果所有测试都通过，说明：
- ✅ 系统配置正确
- ✅ API 连接正常
- ✅ 数据流完整
- ✅ 可以正常运行

### 部分测试失败 ⚠️

如果部分测试失败：
1. 查看错误信息
2. 检查配置（.env 文件）
3. 检查网络连接
4. 检查 API 凭证
5. 查看日志输出

### 所有测试失败 ❌

如果所有测试都失败：
1. 检查环境配置
2. 检查依赖安装
3. 检查 API 凭证
4. 检查网络连接
5. 查看详细错误信息

## 🎉 测试通过后

如果所有测试都通过，你可以：

1. **继续开发**: 在 main 分支上继续开发
2. **部署到生产**: 配置真实的 API URL 和凭证
3. **运行真实交易**: 设置 `dry_run=False` 进行真实交易（谨慎！）

## 📚 相关文档

- [TESTING_GUIDE_DECISION_TO_MARKET.md](./TESTING_GUIDE_DECISION_TO_MARKET.md) - 决策到市场测试指南
- [HOW_DECISION_TO_MARKET_WORKS.md](./HOW_DECISION_TO_MARKET_WORKS.md) - 工作原理
- [SETUP_REAL_API.md](./SETUP_REAL_API.md) - 真实API设置指南

