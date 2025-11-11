# 快速测试命令

## 🚀 测试双AI资金管理功能（推荐）

```bash
python api/agents/dual_ai_example.py
```

**这个命令会测试**:
- ✅ 资本管理器初始化（50000 USD）
- ✅ 资金分配（Qwen和DeepSeek各25000 USD）
- ✅ 市场数据采集
- ✅ 两个AI独立生成决策
- ✅ 资金检查和控制
- ✅ 交易执行（dry_run模式，不会真正下单）

**预计时间**: 20-30秒

---

## 📋 其他测试命令

### 测试完整流程

```bash
python test_complete_flow.py
```

**预计时间**: 2-3分钟

### 快速系统测试

```bash
python test_complete_system.py --quick
```

**预计时间**: 30秒

### 测试Roostoo API连接

```bash
python test_real_api.py
```

**预计时间**: 5-10秒

### 测试决策执行

```bash
python test_decision_to_market.py
```

**预计时间**: 10-15秒

---

## ⚠️ 测试前准备

### 1. 检查环境变量

确保 `.env` 文件包含：

```env
# Qwen API
QWEN_API_KEY=your_qwen_api_key

# DeepSeek API
DEEPSEEK_API_KEY=your_deepseek_api_key

# Roostoo API（可选）
ROOSTOO_API_KEY=your_roostoo_api_key
ROOSTOO_SECRET_KEY=your_roostoo_secret_key
ROOSTOO_API_URL=https://api.roostoo.com
```

### 2. 安装依赖

```bash
pip install requests python-dotenv
```

---

## 🔍 测试输出示例

### 成功输出

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
✓ 资金分配完成: {'qwen_agent': 25000.0, 'deepseek_agent': 25000.0}
✓ Qwen Agent 创建成功
✓ DeepSeek Agent 创建成功
✓ 增强版执行器创建成功
✓ 所有组件已启动
```

---

## 📚 更多信息

查看详细测试指南：
- [TEST_DUAL_AI.md](./TEST_DUAL_AI.md) - 双AI测试详细指南
- [DUAL_AI_CAPITAL_MANAGEMENT.md](./DUAL_AI_CAPITAL_MANAGEMENT.md) - 功能说明文档

