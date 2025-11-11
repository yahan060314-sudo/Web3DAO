# 快速修复检查清单

## 🎯 目标：确保系统能够成功上传到市场

## ✅ 检查清单

### 1. 配置文件检查

- [ ] `.env`文件存在
- [ ] `ROOSTOO_API_URL`已设置（**不是mock API**）
- [ ] `ROOSTOO_API_KEY`已设置
- [ ] `ROOSTOO_SECRET_KEY`已设置
- [ ] `LLM_PROVIDER`已设置
- [ ] LLM API Key已设置（对应provider）

**检查命令**:
```bash
cat .env | grep -E "ROOSTOO_API_URL|ROOSTOO_API_KEY|LLM_PROVIDER|DEEPSEEK_API_KEY"
```

### 2. API URL检查 ⚠️ 最关键

- [ ] `ROOSTOO_API_URL`不是`https://mock-api.roostoo.com`
- [ ] `ROOSTOO_API_URL`是真实的比赛API URL

**检查命令**:
```bash
python -c "from api.roostoo_client import RoostooClient; c=RoostooClient(); print(f'API URL: {c.base_url}')"
```

**预期输出**:
- ✅ `[RoostooClient] ✓ 使用真实API: https://api.roostoo.com`
- ❌ `[RoostooClient] ⚠️ 使用模拟API: https://mock-api.roostoo.com` → **需要修复**

### 3. API连接测试

- [ ] Roostoo API连接成功
- [ ] LLM API连接成功

**测试命令**:
```bash
# 测试Roostoo API
python test_real_api.py

# 测试LLM API
python -m api.llm_clients.example_usage
```

### 4. 代码配置检查

- [ ] `integrated_example.py`中`dry_run`参数正确（默认False，真实交易）
- [ ] 没有硬编码的mock API URL

**检查命令**:
```bash
grep -n "dry_run\|mock-api" api/agents/integrated_example.py
```

## 🔧 快速修复步骤

### 如果API URL是mock API

**问题**: 看到 `[RoostooClient] ⚠️ 使用模拟API: https://mock-api.roostoo.com`

**修复**:
1. 编辑`.env`文件
2. 添加或修改：
   ```env
   ROOSTOO_API_URL=https://api.roostoo.com  # 替换为真实的比赛API URL
   ```
3. 重新运行测试

### 如果LLM API Key未设置

**问题**: LLM调用失败

**修复**:
1. 编辑`.env`文件
2. 添加LLM API Key：
   ```env
   LLM_PROVIDER=deepseek
   DEEPSEEK_API_KEY=sk-your-actual-key-here
   ```
3. 重新测试

### 如果API连接失败

**可能原因**:
1. API URL不正确
2. 比赛还未开始（API服务未启动）
3. 网络问题
4. API凭证错误

**修复**:
1. 确认比赛是否已开始
2. 确认API URL是否正确
3. 确认API凭证是否正确
4. 检查网络连接

## 📋 最小配置示例

**`.env`文件最小配置**:

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

## 🚀 运行系统

### 测试模式（不会真正下单）

```bash
# 设置环境变量
export DRY_RUN=true

# 运行系统
python -m api.agents.integrated_example
```

### 真实交易模式

```bash
# 确保DRY_RUN未设置或为false
unset DRY_RUN
# 或
export DRY_RUN=false

# 运行系统
python -m api.agents.integrated_example
```

## ⚠️ 需要的信息

### 必须提供

1. **真实的Roostoo比赛API URL**
   - 当前未知
   - 需要从比赛文档获取

2. **至少一个LLM API Key**
   - DeepSeek: https://platform.deepseek.com
   - Qwen: https://dashscope.aliyun.com
   - Minimax: https://www.minimax.chat

### 已提供

1. ✅ Roostoo API Key（在SETUP_REAL_API.md中）
2. ✅ Roostoo Secret Key（在SETUP_REAL_API.md中）

