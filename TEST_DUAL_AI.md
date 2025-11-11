# 双AI资金管理功能测试指南

## 🚀 快速测试

### 方法1: 测试双AI交易系统（推荐）

```bash
python api/agents/dual_ai_example.py
```

**这个脚本会测试**:
- ✅ 资本管理器初始化（50000 USD）
- ✅ 资金分配（Qwen和DeepSeek各25000 USD）
- ✅ 市场数据采集
- ✅ 两个AI独立生成决策
- ✅ 资金检查和控制
- ✅ 交易执行（dry_run模式，不会真正下单）

**预计时间**: 20-30秒

---

## 📋 测试前准备

### 1. 检查环境变量

确保 `.env` 文件包含以下配置：

```env
# Qwen API
QWEN_API_KEY=your_qwen_api_key

# DeepSeek API
DEEPSEEK_API_KEY=your_deepseek_api_key

# Roostoo API（可选，用于获取市场数据）
ROOSTOO_API_KEY=your_roostoo_api_key
ROOSTOO_SECRET_KEY=your_roostoo_secret_key
ROOSTOO_API_URL=https://api.roostoo.com
```

### 2. 安装依赖

```bash
pip install requests python-dotenv
```

---

## 🧪 测试命令

### 测试1: 双AI交易系统

```bash
# 运行双AI交易示例
python api/agents/dual_ai_example.py
```

**预期输出**:
```
================================================================================
双AI交易系统示例
================================================================================

配置:
  - 初始资金: 50000 USD
  - Qwen AI: 25000 USD
  - DeepSeek AI: 25000 USD
  - 模式: dry_run (测试模式，不会真正下单)

✓ 消息总线创建成功
✓ 资本管理器创建成功
[CapitalManager] 初始化完成: 初始资金 = 50000.00 USD
✓ 资金分配完成: {'qwen_agent': 25000.0, 'deepseek_agent': 25000.0}
...
```

### 测试2: 完整流程测试

```bash
# 运行完整流程测试
python test_complete_flow.py
```

**这个脚本会测试**:
- ✅ Roostoo API 连接
- ✅ LLM 连接（DeepSeek/Qwen/Minimax）
- ✅ 市场数据采集
- ✅ AI决策生成
- ✅ 决策执行（dry_run模式）
- ✅ 完整流程（端到端）

**预计时间**: 2-3分钟

### 测试3: 快速系统测试

```bash
# 运行快速系统测试
python test_complete_system.py --quick
```

**预计时间**: 30秒

---

## 🔍 测试步骤详解

### 步骤1: 检查环境配置

```bash
# 检查 .env 文件是否存在
ls -la .env

# 检查环境变量是否配置
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

print('QWEN_API_KEY:', '✓' if os.getenv('QWEN_API_KEY') else '✗')
print('DEEPSEEK_API_KEY:', '✓' if os.getenv('DEEPSEEK_API_KEY') else '✗')
print('ROOSTOO_API_KEY:', '✓' if os.getenv('ROOSTOO_API_KEY') else '✗')
"
```

### 步骤2: 测试资本管理器

```bash
python -c "
from api.agents.capital_manager import CapitalManager

# 创建资本管理器
cm = CapitalManager(initial_capital=50000.0)

# 分配资金
allocations = cm.allocate_equal(['qwen_agent', 'deepseek_agent'])
print('分配结果:', allocations)

# 打印摘要
cm.print_summary()
"
```

### 步骤3: 测试Agent创建

```bash
python -c "
from api.agents.manager import AgentManager
from api.agents.bus import MessageBus

bus = MessageBus()
manager = AgentManager()

# 添加Qwen Agent
manager.add_agent(
    name='qwen_agent',
    system_prompt='You are a trading assistant.',
    llm_provider='qwen',
    allocated_capital=25000.0
)

# 添加DeepSeek Agent
manager.add_agent(
    name='deepseek_agent',
    system_prompt='You are a trading assistant.',
    llm_provider='deepseek',
    allocated_capital=25000.0
)

print('✓ Agents created successfully')
print(f'Total agents: {len(manager.agents)}')
"
```

### 步骤4: 运行完整测试

```bash
# 运行双AI交易示例
python api/agents/dual_ai_example.py
```

---

## ✅ 测试通过标准

如果看到以下输出，说明测试通过：

```
================================================================================
双AI交易系统示例
================================================================================

✓ 消息总线创建成功
✓ 资本管理器创建成功
✓ 资金分配完成: {'qwen_agent': 25000.0, 'deepseek_agent': 25000.0}
✓ Qwen Agent 创建成功
✓ DeepSeek Agent 创建成功
✓ 增强版执行器创建成功
✓ 所有组件已启动

等待采集市场数据...
等待决策生成和执行...

执行统计:
  总决策数: 2
  成功执行数: 0-2
  失败执行数: 0-2
  成功率: 0.00%-100.00%

最终资金分配情况:
============================================================
资金分配摘要
============================================================
初始资金: 50000.00 USD
总分配: 50000.00 USD
总使用: 0.00 USD
总可用: 50000.00 USD

各Agent资金分配:
  qwen_agent:
    分配: 25000.00 USD
    使用: 0.00 USD
    可用: 25000.00 USD
  deepseek_agent:
    分配: 25000.00 USD
    使用: 0.00 USD
    可用: 25000.00 USD
============================================================

✓ 所有组件已停止
```

---

## 🐛 常见问题

### 问题1: API Key未配置

**错误**: `DEEPSEEK_API_KEY not set` 或 `QWEN_API_KEY not set`

**解决方法**:
1. 检查 `.env` 文件是否存在
2. 检查 API Key 是否正确配置
3. 确认环境变量已加载

### 问题2: 资金分配失败

**错误**: `资金不足: 已分配 xxx, 请求分配 xxx, 总资金 xxx`

**解决方法**:
1. 检查初始资金设置
2. 检查资金分配逻辑
3. 确保总分配不超过初始资金

### 问题3: Agent无法生成决策

**错误**: `No decisions received` 或 `LLM timeout`

**解决方法**:
1. 检查 LLM API 连接
2. 检查 API Key 是否有效
3. 增加等待时间
4. 检查网络连接

### 问题4: 市场数据采集失败

**错误**: `Error fetching ticker` 或 `Error fetching balance`

**解决方法**:
1. 检查 Roostoo API 连接
2. 检查 API Key 和 Secret Key
3. 如果使用真实API，确保比赛已开始
4. 检查网络连接

---

## 📊 测试输出解读

### 成功输出

- ✅ 所有组件创建成功
- ✅ 资金分配成功
- ✅ 市场数据采集成功
- ✅ AI决策生成成功
- ✅ 资金检查通过
- ✅ 交易执行成功（dry_run模式）

### 警告输出

- ⚠️ API连接问题（可能是网络或配置问题）
- ⚠️ 决策格式问题（AI返回的格式可能不正确）
- ⚠️ 资金不足（交易金额超过可用资金）

### 错误输出

- ✗ API Key未配置
- ✗ 资金分配失败
- ✗ 交易执行失败
- ✗ 网络连接失败

---

## 💡 测试提示

1. **dry_run模式**: 所有测试都使用 `dry_run=True`，不会真正下单
2. **资金跟踪**: 注意观察资金使用情况，确保资金分配正确
3. **决策生成**: 两个AI应该独立生成决策，互不影响
4. **资金检查**: 交易前会检查可用资金，防止超支
5. **错误处理**: 如果交易失败，资金会自动释放

---

## 📚 相关文档

- [DUAL_AI_CAPITAL_MANAGEMENT.md](./DUAL_AI_CAPITAL_MANAGEMENT.md) - 功能说明文档
- [HOW_TO_TEST_COMPLETE_FLOW.md](./HOW_TO_TEST_COMPLETE_FLOW.md) - 完整流程测试指南
- [COMPLETE_FLOW_TEST_GUIDE.md](./COMPLETE_FLOW_TEST_GUIDE.md) - 详细测试指南

---

## 🎉 下一步

测试通过后，你可以：

1. **继续开发**: 在现有基础上添加更多功能
2. **优化策略**: 优化AI的交易策略
3. **真实交易**: 设置 `dry_run=False` 进行真实交易（谨慎！）
4. **监控运行**: 定期检查资金使用情况和交易统计

