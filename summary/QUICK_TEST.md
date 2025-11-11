# 快速测试指南

## 🚀 一键测试完整流程

### 方法1: 运行完整流程测试（推荐）

```bash
python test_complete_flow.py
```

**这个命令会测试**:
1. ✅ Roostoo API 连接
2. ✅ LLM 连接（DeepSeek/Qwen/Minimax）
3. ✅ 市场数据采集
4. ✅ AI决策生成
5. ✅ 决策执行（dry_run模式，不会真正下单）
6. ✅ 完整流程（端到端）

**预计时间**: 2-3分钟

---

## 📋 测试前准备

### 1. 检查 .env 文件

确保 `.env` 文件包含：

```env
# Roostoo API
ROOSTOO_API_KEY=K9IL3ZxCV1bN5mQwE7rT0yUiP2oA8sDdF6gJ1hKIZ4xC9vBnM0qW3eRtY5ul7oPa
ROOSTOO_SECRET_KEY=cV2bN4mQwE6rT8yUiP0oA2sDdF4gJ6hKIZ8xC0vBnM2qW4eRtY6ul0oPaS2d
ROOSTOO_API_URL=https://api.roostoo.com

# LLM (至少一个)
DEEPSEEK_API_KEY=sk-your-key-here
LLM_PROVIDER=deepseek
```

### 2. 安装依赖

```bash
pip install requests python-dotenv
```

---

## 🧪 测试命令

### 完整测试

```bash
# 运行完整流程测试
python test_complete_flow.py
```

### 快速测试（只测试关键功能）

```bash
# 测试 Roostoo API 连接
python test_real_api.py

# 测试决策执行（dry_run模式）
python test_decision_to_market.py
```

### 分步测试

```bash
# 1. 测试 Roostoo API
python -c "from api.roostoo_client import RoostooClient; client = RoostooClient(); print('API URL:', client.base_url); print('Server time:', client.check_server_time())"

# 2. 测试 LLM
python -m api.llm_clients.example_usage

# 3. 测试完整系统
python test_complete_system.py --quick
```

---

## ✅ 测试通过标准

如果看到以下输出，说明测试通过：

```
✓ 步骤1完成: Roostoo API 连接测试
✓ 步骤2完成: LLM 连接测试
✓ 步骤3完成: 市场数据采集测试
✓ 步骤4完成: AI决策生成测试
✓ 步骤5完成: 决策执行测试
✓ 步骤6完成: 完整流程测试

测试结果总结
================================================================================
✓ 通过: 步骤1: Roostoo API
✓ 通过: 步骤2: LLM 连接
✓ 通过: 步骤3: 市场数据采集
✓ 通过: 步骤4: AI决策生成
✓ 通过: 步骤5: 决策执行
✓ 通过: 步骤6: 完整流程
```

---

## 🐛 如果测试失败

### 检查清单

1. ✅ `.env` 文件是否存在？
2. ✅ API 凭证是否正确？
3. ✅ 网络连接是否正常？
4. ✅ 比赛是否已开始（如果使用真实API）？
5. ✅ 依赖是否已安装？

### 查看详细错误

```bash
# 运行测试并查看详细输出
python test_complete_flow.py 2>&1 | tee test_output.log
```

---

## 📚 更多信息

- [COMPLETE_FLOW_TEST_GUIDE.md](./COMPLETE_FLOW_TEST_GUIDE.md) - 详细测试指南
- [TESTING_GUIDE_DECISION_TO_MARKET.md](./TESTING_GUIDE_DECISION_TO_MARKET.md) - 决策到市场测试指南

