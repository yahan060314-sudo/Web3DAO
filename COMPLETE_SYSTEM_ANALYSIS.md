# 完整系统分析与运行流程

## 📋 系统概览

### 当前使用的Agent数量

**实际使用的Agent**: **2个**（在 `integrated_example.py` 中）

1. **conservative_agent** - 保守型交易Agent
2. **balanced_agent** - 平衡型交易Agent

**未使用的Agent**: **1个**（在代码中被注释）

3. **aggressive_agent** - 激进型交易Agent（第58-64行被注释）

**代码位置**: `api/agents/integrated_example.py` 第42-64行

## 🔄 完整运行流程

### 阶段1: 系统初始化

```
1. 创建AgentManager
   └─> 创建MessageBus（消息总线）
       ├─> market_topic: "market_ticks"
       ├─> dialog_topic: "dialog_prompts"
       └─> decision_topic: "decisions"

2. 创建PromptManager
   └─> 加载prompt模板（natural_language_prompt.txt）

3. 创建Agent（2个）
   ├─> conservative_agent
   │   └─> system_prompt: 保守策略
   └─> balanced_agent
       └─> system_prompt: 平衡策略

4. 启动Agent
   └─> 每个Agent在独立线程中运行
       ├─> 订阅market_topic（市场数据）
       └─> 订阅dialog_topic（用户prompt）
```

### 阶段2: 数据采集

```
5. 创建MarketDataCollector
   └─> 定期从Roostoo API获取数据
       ├─> get_ticker(pair) - 每5秒
       └─> get_balance() - 每5秒

6. 数据格式化
   └─> DataFormatter.format_ticker()
   └─> DataFormatter.format_balance()

7. 发布到MessageBus
   └─> 发布到market_topic
       └─> 所有Agent同时接收
```

### 阶段3: Prompt处理

```
8. 创建交易Prompt
   └─> PromptManager.create_trading_prompt()
       └─> 或 create_spot_prompt_from_market_data()

9. 广播Prompt
   └─> AgentManager.broadcast_prompt()
       └─> 发布到dialog_topic
           └─> 所有Agent同时接收
```

### 阶段4: Agent决策生成

```
10. Agent接收Prompt
    └─> BaseAgent._handle_dialog()
        └─> 添加到dialog_history

11. Agent生成决策
    └─> BaseAgent._generate_decision()
        ├─> 构建LLM消息：
        │   ├─> system message: system_prompt
        │   ├─> system message: 市场数据
        │   ├─> user messages: 对话历史（最近5条）
        │   └─> user message: 当前prompt
        │
        ├─> 调用LLM（DeepSeek/Qwen/Minimax）
        │   └─> llm.chat(messages)
        │
        ├─> 验证JSON格式
        │   └─> _validate_json_decision()
        │
        └─> 发布决策
            └─> 发布到decision_topic
```

### 阶段5: 交易执行

```
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
            └─> 真正下单（如果dry_run=False）
```

## 🚨 可能导致失败的因素分析

### 1. API配置问题 ⚠️ 关键

#### 1.1 Roostoo API URL - 可能使用模拟API

**问题位置**:
- `api/roostoo_client.py` 第23行
- `config/config.py` 第13行

**当前状态**:
```python
BASE_URL = os.getenv("ROOSTOO_API_URL", "https://mock-api.roostoo.com")
```

**问题**:
- ❌ 默认使用 `https://mock-api.roostoo.com`（模拟API）
- ❌ 如果 `.env` 文件中没有设置 `ROOSTOO_API_URL`，会使用模拟API
- ❌ 模拟API不会真正下单

**检查方法**:
```bash
# 检查.env文件
cat .env | grep ROOSTOO_API_URL

# 检查代码中的URL
python -c "from api.roostoo_client import RoostooClient; c=RoostooClient(); print(c.base_url)"
```

**解决方案**:
在 `.env` 文件中设置：
```env
ROOSTOO_API_URL=https://api.roostoo.com  # 或真实的比赛API URL
```

**需要的信息**:
- ⚠️ **真实的Roostoo比赛API URL**（当前未知）
- 可能的值：
  - `https://api.roostoo.com`
  - `https://competition-api.roostoo.com`
  - 或其他比赛专用URL

#### 1.2 Roostoo API凭证

**检查位置**:
- `.env` 文件中的 `ROOSTOO_API_KEY` 和 `ROOSTOO_SECRET_KEY`

**问题**:
- ❌ 如果未设置，会抛出异常
- ❌ 如果设置错误，API调用会失败

**检查方法**:
```bash
# 检查.env文件
cat .env | grep ROOSTOO_API_KEY
cat .env | grep ROOSTOO_SECRET_KEY

# 测试API连接
python test_real_api.py
```

**需要的信息**:
- ✅ 根据 `SETUP_REAL_API.md`，API Key和Secret Key已提供
- ⚠️ 需要确认这些凭证是否有效

### 2. LLM配置问题

#### 2.1 LLM Provider配置

**检查位置**:
- `.env` 文件中的 `LLM_PROVIDER`
- 支持的provider: `deepseek`, `qwen`, `minimax`

**问题**:
- ❌ 如果未设置，默认使用 `deepseek`
- ❌ 如果设置的provider不支持，会抛出异常

**检查方法**:
```bash
# 检查.env文件
cat .env | grep LLM_PROVIDER

# 测试LLM连接
python -m api.llm_clients.example_usage
```

#### 2.2 LLM API Key

**检查位置**:
- `.env` 文件中的 `DEEPSEEK_API_KEY` 或 `QWEN_API_KEY` 或 `MINIMAX_API_KEY`

**问题**:
- ❌ 如果未设置，LLM调用会失败
- ❌ 如果设置错误，API调用会失败

**需要的信息**:
- ⚠️ **至少需要一个有效的LLM API Key**
  - DeepSeek API Key（如果使用deepseek）
  - Qwen API Key（如果使用qwen）
  - Minimax API Key（如果使用minimax）

### 3. 代码逻辑问题

#### 3.1 dry_run模式

**问题位置**:
- `api/agents/executor.py` 第21行
- `api/agents/enhanced_executor.py` 第32行

**当前状态**:
- `integrated_example.py` 中 `TradeExecutor` 的 `dry_run` 参数未设置（默认False）
- 但测试文件中使用 `dry_run=True`

**问题**:
- ⚠️ 如果 `dry_run=True`，不会真正下单
- ⚠️ 如果 `dry_run=False` 但API URL是mock，也不会真正下单

**检查方法**:
```python
# 检查executor初始化
executor = TradeExecutor(..., dry_run=False)  # 确保是False
```

#### 3.2 决策解析问题

**问题位置**:
- `api/agents/executor.py` 的 `_parse_decision()` 方法

**潜在问题**:
- ⚠️ JSON格式解析失败
- ⚠️ 自然语言解析失败
- ⚠️ 决策格式不符合要求

**检查方法**:
```bash
# 测试决策解析
python test_decision_to_market.py
```

### 4. 网络和连接问题

#### 4.1 网络连接

**问题**:
- ❌ 无法连接到API服务器
- ❌ 超时错误
- ❌ DNS解析失败

**检查方法**:
```bash
# 测试网络连接
curl -I https://api.roostoo.com
ping api.roostoo.com
```

#### 4.2 API服务状态

**问题**:
- ❌ API服务未启动（比赛还未开始）
- ❌ API服务维护中
- ❌ API服务不可用

**检查方法**:
```bash
# 测试API连接
python test_real_api.py
```

### 5. 数据格式问题

#### 5.1 市场数据格式

**问题位置**:
- `api/agents/data_formatter.py`

**潜在问题**:
- ⚠️ Roostoo API返回的数据格式与预期不符
- ⚠️ 数据解析失败
- ⚠️ 关键字段缺失

**检查方法**:
```bash
# 测试数据格式化
python -c "from api.roostoo_client import RoostooClient; c=RoostooClient(); print(c.get_ticker('BTC/USD'))"
```

#### 5.2 决策格式

**问题位置**:
- `api/agents/base_agent.py` 的 `_generate_decision()`

**潜在问题**:
- ⚠️ LLM输出不符合JSON格式要求
- ⚠️ JSON格式验证失败
- ⚠️ 决策字段缺失

**检查方法**:
```bash
# 测试决策生成
python test_complete_system.py
```

### 6. 环境配置问题

#### 6.1 .env文件

**问题**:
- ❌ `.env` 文件不存在
- ❌ `.env` 文件格式错误
- ❌ 环境变量未正确加载

**检查方法**:
```bash
# 检查.env文件
ls -la .env
cat .env

# 检查环境变量加载
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('ROOSTOO_API_URL'))"
```

#### 6.2 Python依赖

**问题**:
- ❌ 缺少必要的Python包
- ❌ 包版本不兼容

**检查方法**:
```bash
# 检查依赖
pip list | grep -E "requests|dotenv|sqlite"
```

## 📝 需要的信息清单

### ⚠️ 必须提供（否则无法成功运行）

1. **真实的Roostoo比赛API URL**
   - 当前状态：未知
   - 可能的值：
     - `https://api.roostoo.com`
     - `https://competition-api.roostoo.com`
     - 或其他比赛专用URL
   - 获取方式：
     - 查看比赛文档
     - 联系比赛组织者
     - 查看Roostoo官方文档

2. **至少一个有效的LLM API Key**
   - DeepSeek API Key（如果使用deepseek）
   - Qwen API Key（如果使用qwen）
   - Minimax API Key（如果使用minimax）

### ✅ 已提供（根据SETUP_REAL_API.md）

1. **Roostoo API Key**: `K9IL3ZxCV1bN5mQwE7rT0yUiP2oA8sDdF6gJ1hKIZ4xC9vBnM0qW3eRtY5ul7oPa`
2. **Roostoo Secret Key**: `cV2bN4mQwE6rT8yUiP0oA2sDdF4gJ6hKIZ8xC0vBnM2qW4eRtY6ul0oPaS2d`

### ⚠️ 需要确认

1. **Roostoo API凭证是否有效**
   - 需要测试API连接确认

2. **比赛是否已开始**
   - 根据 `SETUP_REAL_API.md`，比赛开始时间：2025年11月10日 晚上8点 HKT
   - 如果比赛未开始，API服务可能未启动

3. **API认证方式**
   - 真实API的认证方式是否与mock API相同
   - 签名算法是否正确

## 🔍 诊断步骤

### 步骤1: 检查配置文件

```bash
# 1. 检查.env文件是否存在
ls -la .env

# 2. 检查关键配置
cat .env | grep -E "ROOSTOO_API_URL|ROOSTOO_API_KEY|LLM_PROVIDER|DEEPSEEK_API_KEY"
```

### 步骤2: 测试API连接

```bash
# 测试Roostoo API连接
python test_real_api.py

# 测试LLM连接
python -m api.llm_clients.example_usage
```

### 步骤3: 测试完整系统（dry_run模式）

```bash
# 测试完整系统（不会真正下单）
python test_decision_to_market.py

# 或测试集成示例（dry_run模式）
python -m api.agents.integrated_example
```

### 步骤4: 检查代码逻辑

```bash
# 检查executor是否使用dry_run
grep -n "dry_run" api/agents/integrated_example.py

# 检查API URL配置
grep -n "ROOSTOO_API_URL\|mock-api" api/roostoo_client.py config/config.py
```

## 🛠️ 修复建议

### 修复1: 配置真实API URL

**在 `.env` 文件中添加**:
```env
ROOSTOO_API_URL=https://api.roostoo.com  # 替换为真实的比赛API URL
```

### 修复2: 确认LLM配置

**在 `.env` 文件中确认**:
```env
LLM_PROVIDER=deepseek  # 或 qwen 或 minimax
DEEPSEEK_API_KEY=sk-your-actual-key-here  # 如果使用deepseek
```

### 修复3: 确认dry_run设置

**在 `integrated_example.py` 中确认**:
```python
executor = TradeExecutor(
    bus=mgr.bus,
    decision_topic=mgr.decision_topic,
    default_pair="BTC/USD",
    dry_run=False  # 确保是False（真实交易）
)
```

### 修复4: 测试API连接

**运行测试脚本**:
```bash
python test_real_api.py
```

## 📊 系统状态检查清单

### 配置检查

- [ ] `.env` 文件存在
- [ ] `ROOSTOO_API_URL` 已设置（不是mock API）
- [ ] `ROOSTOO_API_KEY` 已设置
- [ ] `ROOSTOO_SECRET_KEY` 已设置
- [ ] `LLM_PROVIDER` 已设置
- [ ] LLM API Key已设置（对应provider）

### 连接检查

- [ ] Roostoo API连接成功
- [ ] LLM API连接成功
- [ ] 网络连接正常

### 代码检查

- [ ] `dry_run=False`（真实交易模式）
- [ ] API URL不是mock API
- [ ] 决策解析正常
- [ ] 数据格式化正常

### 功能检查

- [ ] 市场数据采集正常
- [ ] Agent决策生成正常
- [ ] 决策解析正常
- [ ] 交易执行正常（如果dry_run=False）

## 🎯 下一步行动

1. **确认真实的Roostoo比赛API URL**
   - 查看比赛文档
   - 联系比赛组织者
   - 或尝试常见的URL

2. **配置.env文件**
   - 设置 `ROOSTOO_API_URL` 为真实URL
   - 确认所有API Key已设置

3. **运行测试**
   - 先运行 `test_real_api.py` 测试API连接
   - 再运行 `test_decision_to_market.py` 测试完整流程

4. **确认比赛状态**
   - 确认比赛是否已开始
   - 如果未开始，等待比赛开始后再测试

5. **准备真实交易**
   - 确认所有配置正确
   - 确认API连接成功
   - 设置 `dry_run=False` 进行真实交易

