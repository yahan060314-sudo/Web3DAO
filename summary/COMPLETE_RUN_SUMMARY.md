# 完整系统运行总结

## 📊 系统概览

### Agent使用情况

**实际使用的Agent**: **2个**
1. `conservative_agent` - 保守型交易Agent（风险等级：conservative）
2. `balanced_agent` - 平衡型交易Agent（风险等级：moderate）

**未使用的Agent**: **1个**
3. `aggressive_agent` - 激进型交易Agent（在代码中被注释，未使用）

**代码位置**: `api/agents/integrated_example.py` 第42-64行

### 主入口文件

**推荐使用**: `api/agents/integrated_example.py`

**运行方式**:
```bash
python -m api.agents.integrated_example
```

## 🔄 完整运行流程

### 1. 系统初始化阶段

```
创建AgentManager
  └─> 创建MessageBus（3个topic）
      ├─> market_topic: "market_ticks"
      ├─> dialog_topic: "dialog_prompts"
      └─> decision_topic: "decisions"

创建PromptManager
  └─> 加载natural_language_prompt.txt模板

创建2个Agent
  ├─> conservative_agent（保守策略）
  └─> balanced_agent（平衡策略）

启动Agent线程
  └─> 每个Agent订阅market_topic和dialog_topic
```

### 2. 数据采集阶段

```
MarketDataCollector启动
  └─> 每5秒从Roostoo API获取数据
      ├─> get_ticker("BTC/USD")
      └─> get_balance()

数据格式化
  └─> DataFormatter.format_ticker()
  └─> DataFormatter.format_balance()

发布到MessageBus
  └─> 发布到market_topic
      └─> 所有Agent同时接收并聚合为market_snapshot
```

### 3. Prompt处理阶段

```
创建交易Prompt
  └─> PromptManager.create_trading_prompt()
      或 create_spot_prompt_from_market_data()

广播Prompt
  └─> AgentManager.broadcast_prompt()
      └─> 发布到dialog_topic
          └─> 所有Agent同时接收
```

### 4. Agent决策生成阶段

```
Agent接收Prompt
  └─> BaseAgent._handle_dialog()
      └─> 添加到dialog_history

Agent生成决策
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
```

### 5. 交易执行阶段

```
TradeExecutor接收决策
  └─> 订阅decision_topic
      └─> 接收Agent决策

解析决策
  └─> _parse_decision()
      ├─> 优先解析JSON格式
      └─> 回退到自然语言解析

执行交易
  └─> _maybe_execute()
      ├─> 检查限频（61秒）
      ├─> 解析决策参数
      └─> 调用RoostooClient.place_order()
          └─> 真正下单（如果dry_run=False且API URL是真实的）
```

## 🚨 可能导致失败的因素

### 1. API URL使用模拟API ⚠️ 最严重

**问题**:
- 默认使用`https://mock-api.roostoo.com`（模拟API）
- 模拟API不会真正下单

**检查**:
```bash
python -c "from api.roostoo_client import RoostooClient; c=RoostooClient(); print(f'API URL: {c.base_url}')"
```

**修复**:
在`.env`文件中设置：
```env
ROOSTOO_API_URL=https://api.roostoo.com  # 替换为真实的比赛API URL
```

### 2. LLM API Key未配置

**问题**:
- 如果LLM API Key未设置，Agent无法生成决策

**检查**:
```bash
cat .env | grep -E "LLM_PROVIDER|DEEPSEEK_API_KEY"
```

**修复**:
在`.env`文件中设置LLM API Key

### 3. API凭证错误

**问题**:
- Roostoo API Key或Secret Key错误
- 会导致API调用失败

**检查**:
```bash
python test_real_api.py
```

### 4. 比赛未开始

**问题**:
- 如果比赛未开始，API服务可能未启动
- 会导致连接失败

**检查**:
- 确认比赛开始时间（2025年11月10日 晚上8点 HKT）
- 测试API连接

### 5. dry_run模式

**问题**:
- 如果`dry_run=True`，不会真正下单

**检查**:
```bash
grep -n "dry_run" api/agents/integrated_example.py
```

**修复**:
- 默认是`dry_run=False`（真实交易）
- 可以通过环境变量`DRY_RUN=true`设置为测试模式

### 6. 决策格式问题

**问题**:
- LLM输出不符合JSON格式要求
- 会导致决策被拒绝

**检查**:
```bash
python test_decision_to_market.py
```

## ⚠️ 需要的信息

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
   - **配置位置**: `.env`文件中的`ROOSTOO_API_URL`

2. **至少一个有效的LLM API Key**
   - **DeepSeek API Key**（如果使用deepseek）
     - 获取: https://platform.deepseek.com
   - **Qwen API Key**（如果使用qwen）
     - 获取: https://dashscope.aliyun.com
   - **Minimax API Key**（如果使用minimax）
     - 获取: https://www.minimax.chat
   - **配置位置**: `.env`文件中的对应API Key

### ✅ 已提供

1. **Roostoo API Key**: `K9IL3ZxCV1bN5mQwE7rT0yUiP2oA8sDdF6gJ1hKIZ4xC9vBnM0qW3eRtY5ul7oPa`
2. **Roostoo Secret Key**: `cV2bN4mQwE6rT8yUiP0oA2sDdF4gJ6hKIZ8xC0vBnM2qW4eRtY6ul0oPaS2d`

### ⚠️ 需要确认

1. **Roostoo API凭证是否有效** - 需要测试确认
2. **比赛是否已开始** - 如果未开始，API服务可能未启动
3. **真实API的认证方式** - 是否与mock API相同

## 🔧 快速修复步骤

### 步骤1: 检查.env文件

```bash
# 检查.env文件是否存在
ls -la .env

# 检查关键配置
cat .env | grep -E "ROOSTOO_API_URL|ROOSTOO_API_KEY|LLM_PROVIDER|DEEPSEEK_API_KEY"
```

### 步骤2: 配置.env文件

**最小配置**:
```env
# Roostoo API（必须）
ROOSTOO_API_KEY=K9IL3ZxCV1bN5mQwE7rT0yUiP2oA8sDdF6gJ1hKIZ4xC9vBnM0qW3eRtY5ul7oPa
ROOSTOO_SECRET_KEY=cV2bN4mQwE6rT8yUiP0oA2sDdF4gJ6hKIZ8xC0vBnM2qW4eRtY6ul0oPaS2d
ROOSTOO_API_URL=https://api.roostoo.com  # ⚠️ 需要确认真实的URL

# LLM（必须至少一个）
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-actual-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

### 步骤3: 测试API连接

```bash
# 测试Roostoo API
python test_real_api.py

# 测试LLM API
python -m api.llm_clients.example_usage
```

### 步骤4: 运行系统

```bash
# 测试模式（不会真正下单）
export DRY_RUN=true
python -m api.agents.integrated_example

# 真实交易模式
unset DRY_RUN
python -m api.agents.integrated_example
```

## 📋 诊断命令

### 检查API URL

```bash
python -c "from api.roostoo_client import RoostooClient; c=RoostooClient(); print(f'API URL: {c.base_url}')"
```

**预期输出**:
- ✅ `[RoostooClient] ✓ 使用真实API: https://api.roostoo.com`
- ❌ `[RoostooClient] ⚠️ 使用模拟API: https://mock-api.roostoo.com` → **需要修复**

### 检查配置

```bash
# 检查所有关键配置
cat .env | grep -E "ROOSTOO_API_URL|ROOSTOO_API_KEY|LLM_PROVIDER|DEEPSEEK_API_KEY"
```

### 测试连接

```bash
# 测试Roostoo API
python test_real_api.py

# 测试LLM API
python -m api.llm_clients.example_usage

# 测试完整系统
python test_complete_system.py
```

## 🎯 总结

### 当前状态

- ✅ **代码逻辑完整** - 所有功能都已实现
- ✅ **2个Agent正在使用** - conservative_agent和balanced_agent
- ⚠️ **1个Agent未使用** - aggressive_agent（被注释，不影响运行）
- ❌ **API URL可能使用模拟API** - **这是最可能的问题**
- ⚠️ **需要LLM API Key** - 至少配置一个

### 最可能的问题

**"没有成功上传到市场"的最可能原因**:
1. ❌ **API URL使用模拟API**（最可能，90%概率）
2. ❌ **LLM API Key未配置**（导致Agent无法生成决策）
3. ❌ **API凭证错误**（导致API调用失败）
4. ❌ **比赛未开始**（API服务未启动）

### 必须解决的问题

1. **配置真实的Roostoo API URL**（最重要）
2. **配置LLM API Key**
3. **确认API凭证有效**
4. **确认比赛已开始**（如果API服务未启动）

### 需要的信息

1. ⚠️ **真实的Roostoo比赛API URL**（当前未知，需要从比赛文档获取）
2. ⚠️ **至少一个有效的LLM API Key**（需要从对应平台获取）

### 下一步行动

1. **获取真实的Roostoo比赛API URL**
   - 查看比赛文档
   - 联系比赛组织者
   - 或尝试常见的URL（`https://api.roostoo.com`）

2. **配置.env文件**
   - 设置`ROOSTOO_API_URL`为真实URL
   - 设置LLM API Key

3. **运行测试**
   - `python test_real_api.py` - 测试API连接
   - `python -m api.llm_clients.example_usage` - 测试LLM连接

4. **启动系统**
   - `python -m api.agents.integrated_example` - 运行完整系统

