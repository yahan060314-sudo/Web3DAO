# 最终诊断与修复指南

## 📊 系统运行流程总结

### 主入口文件

**推荐使用**: `api/agents/integrated_example.py`

**运行方式**:
```bash
python -m api.agents.integrated_example
```

### 完整运行流程

```
┌─────────────────────────────────────────────────────────┐
│ 阶段1: 系统初始化                                        │
└─────────────────────────────────────────────────────────┘
1. 创建AgentManager
   └─> 创建MessageBus（3个topic: market_ticks, dialog_prompts, decisions）

2. 创建PromptManager
   └─> 加载natural_language_prompt.txt模板

3. 创建2个Agent
   ├─> conservative_agent（保守策略）
   └─> balanced_agent（平衡策略）
   ⚠️ aggressive_agent（激进策略）- 未使用（代码中被注释）

4. 启动Agent线程
   └─> 每个Agent订阅market_topic和dialog_topic

┌─────────────────────────────────────────────────────────┐
│ 阶段2: 数据采集                                          │
└─────────────────────────────────────────────────────────┘
5. 创建MarketDataCollector
   └─> 每5秒从Roostoo API获取数据
       ├─> get_ticker("BTC/USD")
       └─> get_balance()

6. 数据格式化
   └─> DataFormatter.format_ticker()
   └─> DataFormatter.format_balance()

7. 发布到MessageBus
   └─> 发布到market_topic
       └─> 所有Agent同时接收并聚合

┌─────────────────────────────────────────────────────────┐
│ 阶段3: Prompt处理                                        │
└─────────────────────────────────────────────────────────┘
8. 创建交易Prompt
   └─> PromptManager.create_trading_prompt()
       └─> 或 create_spot_prompt_from_market_data()

9. 广播Prompt
   └─> AgentManager.broadcast_prompt()
       └─> 发布到dialog_topic
           └─> 所有Agent同时接收

┌─────────────────────────────────────────────────────────┐
│ 阶段4: Agent决策生成                                     │
└─────────────────────────────────────────────────────────┘
10. Agent接收Prompt
    └─> BaseAgent._handle_dialog()
        └─> 添加到dialog_history

11. Agent生成决策
    └─> BaseAgent._generate_decision()
        ├─> 构建LLM消息：
        │   ├─> system: system_prompt（每个Agent不同）
        │   ├─> system: 市场数据
        │   ├─> user: 对话历史（最近5条）
        │   └─> user: 当前prompt（统一广播）
        │
        ├─> 调用LLM（DeepSeek/Qwen/Minimax）
        │   └─> llm.chat(messages)
        │
        ├─> 验证JSON格式
        │   └─> _validate_json_decision()
        │
        └─> 发布决策到decision_topic

┌─────────────────────────────────────────────────────────┐
│ 阶段5: 交易执行                                          │
└─────────────────────────────────────────────────────────┘
12. TradeExecutor接收决策
    └─> 订阅decision_topic
        └─> 接收Agent决策

13. 解析决策
    └─> _parse_decision()
        ├─> 优先解析JSON格式
        └─> 回退到自然语言解析

14. 执行交易
    └─> _maybe_execute()
        ├─> 检查限频（61秒）
        ├─> 解析决策参数
        └─> 调用RoostooClient.place_order()
            └─> 真正下单（如果dry_run=False且API URL是真实的）
```

### Agent使用情况

**实际使用的Agent**: **2个**
1. `conservative_agent` - 保守型交易Agent
2. `balanced_agent` - 平衡型交易Agent

**未使用的Agent**: **1个**
3. `aggressive_agent` - 激进型交易Agent（在`integrated_example.py`第58-64行被注释）

**代码位置**: `api/agents/integrated_example.py` 第42-64行

## 🚨 关键问题诊断

### 问题1: API URL可能使用模拟API ⚠️ 最严重

**问题位置**:
- `api/roostoo_client.py` 第23行
- `config/config.py` 第13行

**当前代码**:
```python
BASE_URL = os.getenv("ROOSTOO_API_URL", "https://mock-api.roostoo.com")
```

**问题**:
- ❌ 如果`.env`文件中没有设置`ROOSTOO_API_URL`，默认使用`https://mock-api.roostoo.com`
- ❌ 模拟API不会真正下单
- ❌ 即使`dry_run=False`，如果API URL是mock，也不会真正下单

**检查方法**:
```bash
# 方法1: 检查.env文件
cat .env | grep ROOSTOO_API_URL

# 方法2: 检查代码中的实际URL
python -c "from api.roostoo_client import RoostooClient; c=RoostooClient(); print(f'API URL: {c.base_url}')"
```

**预期输出**:
- ❌ 如果使用mock API: `[RoostooClient] ⚠️ 使用模拟API: https://mock-api.roostoo.com`
- ✅ 如果使用真实API: `[RoostooClient] ✓ 使用真实API: https://api.roostoo.com`

**修复方法**:
在`.env`文件中添加：
```env
ROOSTOO_API_URL=https://api.roostoo.com  # 替换为真实的比赛API URL
```

### 问题2: dry_run参数未明确设置

**问题位置**:
- `api/agents/integrated_example.py` 第84-88行

**当前代码**:
```python
executor = TradeExecutor(
    bus=mgr.bus,
    decision_topic=mgr.decision_topic,
    default_pair="BTC/USD"
    # ⚠️ dry_run参数未设置，默认是False（真实交易）
)
```

**问题**:
- ⚠️ 虽然默认是`dry_run=False`（真实交易），但没有明确设置
- ⚠️ 如果API URL是mock，即使`dry_run=False`也不会真正下单

**修复方法**:
明确设置`dry_run=False`（如果确实要真实交易）：
```python
executor = TradeExecutor(
    bus=mgr.bus,
    decision_topic=mgr.decision_topic,
    default_pair="BTC/USD",
    dry_run=False  # 明确设置为False（真实交易）
)
```

### 问题3: LLM API Key可能未配置

**检查位置**:
- `.env`文件中的`DEEPSEEK_API_KEY`或`QWEN_API_KEY`或`MINIMAX_API_KEY`
- `.env`文件中的`LLM_PROVIDER`

**问题**:
- ❌ 如果LLM API Key未设置，Agent无法生成决策
- ❌ 如果LLM Provider未设置，默认使用deepseek，但如果没有API Key会失败

**检查方法**:
```bash
# 检查LLM配置
cat .env | grep -E "LLM_PROVIDER|DEEPSEEK_API_KEY|QWEN_API_KEY|MINIMAX_API_KEY"

# 测试LLM连接
python -m api.llm_clients.example_usage
```

### 问题4: Roostoo API凭证可能未配置

**检查位置**:
- `.env`文件中的`ROOSTOO_API_KEY`和`ROOSTOO_SECRET_KEY`

**问题**:
- ❌ 如果未设置，会抛出异常
- ❌ 如果设置错误，API调用会失败

**检查方法**:
```bash
# 检查API凭证
cat .env | grep -E "ROOSTOO_API_KEY|ROOSTOO_SECRET_KEY"

# 测试API连接
python test_real_api.py
```

### 问题5: 决策格式验证可能失败

**问题位置**:
- `api/agents/base_agent.py` 的 `_validate_json_decision()`
- `api/agents/executor.py` 的 `_parse_decision()`

**问题**:
- ⚠️ LLM可能不输出JSON格式
- ⚠️ JSON格式验证失败会导致决策被拒绝

**检查方法**:
```bash
# 测试决策生成和解析
python test_decision_to_market.py
```

## 🔧 修复步骤

### 步骤1: 检查并配置.env文件

**创建或编辑`.env`文件**:

```env
# ============================================
# Roostoo API配置（比赛凭证）
# ============================================
ROOSTOO_API_KEY=K9IL3ZxCV1bN5mQwE7rT0yUiP2oA8sDdF6gJ1hKIZ4xC9vBnM0qW3eRtY5ul7oPa
ROOSTOO_SECRET_KEY=cV2bN4mQwE6rT8yUiP0oA2sDdF4gJ6hKIZ8xC0vBnM2qW4eRtY6ul0oPaS2d

# ⚠️ 重要: 需要设置真实的比赛API URL
# 如果不知道真实URL，可以先尝试以下值：
# - https://api.roostoo.com
# - https://competition-api.roostoo.com
# 或查看比赛文档获取正确的URL
ROOSTOO_API_URL=https://api.roostoo.com

# ============================================
# LLM配置（至少配置一个）
# ============================================
# 选择LLM提供商: deepseek | qwen | minimax
LLM_PROVIDER=deepseek

# DeepSeek配置（如果使用deepseek）
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# Qwen配置（如果使用qwen）
# QWEN_API_KEY=your_qwen_api_key
# QWEN_BASE_URL=https://api.qwen.ai
# QWEN_MODEL=qwen-chat

# Minimax配置（如果使用minimax）
# MINIMAX_API_KEY=your_minimax_api_key
# MINIMAX_BASE_URL=https://api.minimax.chat
# MINIMAX_MODEL=abab5.5-chat
```

### 步骤2: 确认API URL

**运行测试脚本**:
```bash
python test_real_api.py
```

**检查输出**:
- ✅ 如果看到 `[RoostooClient] ✓ 使用真实API: https://api.roostoo.com` → 配置正确
- ❌ 如果看到 `[RoostooClient] ⚠️ 使用模拟API: https://mock-api.roostoo.com` → 需要设置`ROOSTOO_API_URL`

### 步骤3: 测试LLM连接

**运行测试**:
```bash
python -m api.llm_clients.example_usage
```

**检查输出**:
- ✅ 如果成功返回LLM响应 → LLM配置正确
- ❌ 如果失败 → 检查LLM API Key是否正确

### 步骤4: 修改integrated_example.py确保真实交易

**修改位置**: `api/agents/integrated_example.py` 第84-88行

**修改前**:
```python
executor = TradeExecutor(
    bus=mgr.bus,
    decision_topic=mgr.decision_topic,
    default_pair="BTC/USD"
)
```

**修改后**:
```python
executor = TradeExecutor(
    bus=mgr.bus,
    decision_topic=mgr.decision_topic,
    default_pair="BTC/USD",
    dry_run=False  # 明确设置为False（真实交易）
)
```

### 步骤5: 运行完整系统测试

**运行测试**:
```bash
# 先运行完整系统测试（dry_run模式）
python test_complete_system.py

# 如果测试通过，运行集成示例
python -m api.agents.integrated_example
```

## ⚠️ 需要的信息清单

### 🔴 必须提供（否则无法成功运行）

1. **真实的Roostoo比赛API URL**
   - **当前状态**: ❌ 未知
   - **可能的值**:
     - `https://api.roostoo.com`
     - `https://competition-api.roostoo.com`
     - 或其他比赛专用URL
   - **获取方式**:
     - 查看比赛文档或邮件
     - 联系比赛组织者
     - 查看Roostoo官方文档
     - 在比赛开始后测试连接
   - **配置位置**: `.env`文件中的`ROOSTOO_API_URL`

2. **至少一个有效的LLM API Key**
   - **DeepSeek API Key**（如果使用deepseek）
     - 获取方式: https://platform.deepseek.com
   - **Qwen API Key**（如果使用qwen）
     - 获取方式: https://dashscope.aliyun.com
   - **Minimax API Key**（如果使用minimax）
     - 获取方式: https://www.minimax.chat
   - **配置位置**: `.env`文件中的对应API Key

### ✅ 已提供（根据SETUP_REAL_API.md）

1. **Roostoo API Key**: `K9IL3ZxCV1bN5mQwE7rT0yUiP2oA8sDdF6gJ1hKIZ4xC9vBnM0qW3eRtY5ul7oPa`
2. **Roostoo Secret Key**: `cV2bN4mQwE6rT8yUiP0oA2sDdF4gJ6hKIZ8xC0vBnM2qW4eRtY6ul0oPaS2d`

### ⚠️ 需要确认

1. **Roostoo API凭证是否有效**
   - 需要运行`python test_real_api.py`测试确认

2. **比赛是否已开始**
   - 根据`SETUP_REAL_API.md`，比赛开始时间：2025年11月10日 晚上8点 HKT
   - 如果比赛未开始，API服务可能未启动

3. **真实API的认证方式**
   - 真实API的认证方式是否与mock API相同
   - 签名算法是否正确

## 🔍 完整诊断检查清单

### 配置检查

```bash
# 1. 检查.env文件是否存在
ls -la .env

# 2. 检查关键配置
cat .env | grep -E "ROOSTOO_API_URL|ROOSTOO_API_KEY|LLM_PROVIDER|DEEPSEEK_API_KEY"

# 3. 检查API URL是否使用mock
python -c "from api.roostoo_client import RoostooClient; c=RoostooClient(); print(f'API URL: {c.base_url}')"
```

### 连接检查

```bash
# 1. 测试Roostoo API连接
python test_real_api.py

# 2. 测试LLM连接
python -m api.llm_clients.example_usage

# 3. 测试网络连接
curl -I https://api.roostoo.com
```

### 代码检查

```bash
# 1. 检查executor的dry_run设置
grep -n "dry_run" api/agents/integrated_example.py

# 2. 检查API URL配置
grep -n "ROOSTOO_API_URL\|mock-api" api/roostoo_client.py config/config.py

# 3. 检查Agent数量
grep -n "add_agent\|aggressive_agent" api/agents/integrated_example.py
```

### 功能检查

```bash
# 1. 测试完整系统（dry_run模式）
python test_complete_system.py

# 2. 测试决策解析
python test_decision_to_market.py

# 3. 测试集成示例（需要先配置好API）
python -m api.agents.integrated_example
```

## 🎯 快速修复指南

### 如果"没有成功上传到市场"

**最可能的原因**:
1. ❌ **API URL使用模拟API**（最可能）
2. ❌ **dry_run=True**（测试模式）
3. ❌ **API凭证错误**
4. ❌ **比赛未开始**（API服务未启动）

**快速检查**:
```bash
# 1. 检查API URL
python -c "from api.roostoo_client import RoostooClient; c=RoostooClient(); print(f'API URL: {c.base_url}')"

# 2. 如果显示mock API，需要设置ROOSTOO_API_URL
# 编辑.env文件，添加：
# ROOSTOO_API_URL=https://api.roostoo.com

# 3. 测试API连接
python test_real_api.py
```

**修复步骤**:
1. ✅ 在`.env`文件中设置`ROOSTOO_API_URL`为真实URL
2. ✅ 确认`ROOSTOO_API_KEY`和`ROOSTOO_SECRET_KEY`已设置
3. ✅ 确认`dry_run=False`（在`integrated_example.py`中）
4. ✅ 运行`python test_real_api.py`测试连接
5. ✅ 如果连接成功，运行`python -m api.agents.integrated_example`

## 📝 总结

### 当前状态

- ✅ **代码逻辑完整** - 所有功能都已实现
- ✅ **2个Agent正在使用** - conservative_agent和balanced_agent
- ⚠️ **1个Agent未使用** - aggressive_agent（被注释）
- ❌ **API URL可能使用模拟API** - 需要配置真实URL
- ⚠️ **需要LLM API Key** - 至少配置一个

### 必须解决的问题

1. **配置真实的Roostoo API URL**（最重要）
2. **配置LLM API Key**
3. **确认API凭证有效**
4. **确认比赛已开始**（如果API服务未启动）

### 需要的信息

1. ⚠️ **真实的Roostoo比赛API URL**（当前未知，需要从比赛文档获取）
2. ⚠️ **至少一个有效的LLM API Key**（需要从对应平台获取）

### 下一步行动

1. 获取真实的Roostoo比赛API URL
2. 配置`.env`文件（设置`ROOSTOO_API_URL`和LLM API Key）
3. 运行`python test_real_api.py`测试API连接
4. 如果连接成功，运行`python -m api.agents.integrated_example`启动系统

