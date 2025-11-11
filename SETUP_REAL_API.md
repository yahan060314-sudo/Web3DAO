# 配置真实 Roostoo API 指南

## 📋 比赛信息

- **比赛开始时间**: 2025年11月10日 晚上8点 HKT
- **API Key**: `K9IL3ZxCV1bN5mQwE7rT0yUiP2oA8sDdF6gJ1hKIZ4xC9vBnM0qW3eRtY5ul7oPa`
- **API Secret**: `cV2bN4mQwE6rT8yUiP0oA2sDdF4gJ6hKIZ8xC0vBnM2qW4eRtY6ul0oPaS2d`

## 🔧 配置步骤

### 步骤1: 创建 .env 文件

在项目根目录创建 `.env` 文件：

```bash
# 如果 .env 文件不存在，创建它
touch .env
```

### 步骤2: 配置API凭证

编辑 `.env` 文件，添加以下内容：

```env
# Roostoo API Configuration (Official Competition)
ROOSTOO_API_KEY=K9IL3ZxCV1bN5mQwE7rT0yUiP2oA8sDdF6gJ1hKIZ4xC9vBnM0qW3eRtY5ul7oPa
ROOSTOO_SECRET_KEY=cV2bN4mQwE6rT8yUiP0oA2sDdF4gJ6hKIZ8xC0vBnM2qW4eRtY6ul0oPaS2d

# API URL (需要确认真实的比赛API URL)
# 请替换为真实的比赛API URL
ROOSTOO_API_URL=https://api.roostoo.com

# LLM Configuration (至少配置一个)
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# LLM Provider Selection
LLM_PROVIDER=deepseek
```

### 步骤3: 确认真实的API URL

**重要**: 需要确认真实的比赛API URL。

**可能的值**:
- `https://api.roostoo.com`
- `https://competition-api.roostoo.com`
- 或其他比赛专用URL

**如何确认**:
1. 查看比赛文档或邮件
2. 联系比赛组织者
3. 查看Roostoo官方文档

**如果不知道真实的API URL**:
- 可以先使用 `https://api.roostoo.com` 测试
- 如果连接失败，尝试其他可能的URL
- 或者等待比赛开始后测试

## 🧪 测试步骤

### 测试1: 测试API连接

```bash
# 测试真实API连接
python test_real_api.py
```

**预期输出**:
```
测试真实 Roostoo API 连接
================================================================================

配置检查:
  API URL: https://api.roostoo.com
  API Key: K9IL3ZxCV1...
  Secret Key: cV2bN4mQwE...

创建 RoostooClient...
✓ 客户端创建成功
  使用的API URL: https://api.roostoo.com

测试1: 检查服务器时间...
✓ 服务器时间获取成功
  响应: {'ServerTime': ...}
```

### 测试2: 测试完整系统（dry_run模式）

```bash
# 测试完整系统（不会真正下单）
python test_decision_to_market.py
```

### 测试3: 测试增强版执行器（dry_run模式）

```bash
# 测试增强版执行器（不会真正下单）
python -m api.agents.enhanced_example
```

## ⚠️ 重要注意事项

### 1. 比赛开始时间

- **比赛开始**: 2025年11月10日 晚上8点 HKT
- **在此之前**: API服务可能未启动，测试可能会失败
- **建议**: 在比赛开始后再进行真实API测试

### 2. 安全测试

**在比赛开始前，建议**:
- ✅ 使用 `dry_run=True` 模式测试
- ✅ 测试API连接
- ✅ 测试决策解析
- ✅ 测试完整流程

**在比赛开始后，可以**:
- ✅ 测试真实API连接
- ✅ 测试获取市场数据
- ✅ 测试获取账户余额
- ✅ 使用 `dry_run=False` 进行真实交易（谨慎！）

### 3. API URL确认

**如果API连接失败，可能的原因**:
1. API URL不正确
2. 比赛还未开始（API服务未启动）
3. 网络问题
4. API凭证不正确

## 🔍 故障排查

### 问题1: API连接失败

**错误信息**: `Connection failed` 或 `HTTP Error`

**解决方法**:
1. 检查API URL是否正确
2. 检查网络连接
3. 确认比赛是否已开始
4. 检查API Key和Secret Key是否正确

### 问题2: 认证失败

**错误信息**: `401 Unauthorized` 或 `403 Forbidden`

**解决方法**:
1. 检查API Key和Secret Key是否正确
2. 检查签名算法是否正确
3. 检查时间戳是否正确

### 问题3: API服务未启动

**错误信息**: `Connection refused` 或 `Timeout`

**解决方法**:
1. 确认比赛是否已开始
2. 等待比赛开始后再测试
3. 检查API URL是否正确

## 📝 测试检查清单

### 比赛开始前

- [ ] ✅ 创建 `.env` 文件
- [ ] ✅ 配置API凭证
- [ ] ✅ 配置API URL（如果知道）
- [ ] ✅ 测试代码（dry_run模式）
- [ ] ✅ 测试决策解析
- [ ] ✅ 测试完整流程

### 比赛开始后

- [ ] ✅ 测试API连接
- [ ] ✅ 测试获取市场数据
- [ ] ✅ 测试获取账户余额
- [ ] ✅ 测试下单功能（dry_run模式）
- [ ] ✅ 测试完整交易流程
- [ ] ✅ 准备进行真实交易

## 🚀 快速开始

### 1. 创建 .env 文件

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env 文件，添加真实的API凭证
# 注意: API凭证已经配置在 .env.example 中
```

### 2. 确认API URL

```bash
# 编辑 .env 文件，设置真实的API URL
# ROOSTOO_API_URL=https://api.roostoo.com
```

### 3. 测试连接

```bash
# 测试真实API连接
python test_real_api.py
```

### 4. 测试完整系统

```bash
# 测试完整系统（dry_run模式）
python test_decision_to_market.py
```

## 📞 需要帮助？

如果遇到问题，请检查：

1. **.env文件**: 是否创建并配置正确？
2. **API URL**: 是否正确？
3. **比赛状态**: 比赛是否已开始？
4. **网络连接**: 是否正常？
5. **API凭证**: 是否正确？

## 🎯 下一步

1. ✅ 创建 `.env` 文件并配置API凭证
2. ✅ 确认真实的API URL
3. ✅ 运行测试脚本验证连接
4. ✅ 等待比赛开始
5. ✅ 在比赛开始后测试真实API
6. ✅ 准备进行真实交易

