# 快速开始指南

## 系统特性

✅ **两个Agent平分本金**：初始资金平均分配给两个Agent，各自独立操作  
✅ **全局决策频率限制**：整个bot在一分钟内最多输出1次决策  
✅ **API调用频率限制**：每分钟最多5次API调用  
✅ **真实交易执行**：决策通过API正确传到市场  
✅ **持续运行**：适合在tmux中持续运行，即使断开SSH连接也不会停止  

## 快速运行

### 1. 确保环境配置正确

检查 `.env` 文件：

```bash
cat .env
```

必须包含：
- `ROOSTOO_API_KEY` - Roostoo API密钥
- `ROOSTOO_SECRET_KEY` - Roostoo API密钥
- `ROOSTOO_API_URL` - Roostoo API地址（例如：`https://mock-api.roostoo.com`）
- 至少一个LLM API KEY：
  - `DEEPSEEK_API_KEY` 或
  - `QWEN_API_KEY` 或
  - `MINIMAX_API_KEY`

### 2. 在tmux中运行

```bash
# 进入项目目录
cd /path/to/Web3DAO

# 创建tmux会话并运行bot
tmux new-session -d -s trading_bot 'python run_bot.py'

# 查看运行状态
tmux attach -t trading_bot
```

### 3. 停止运行

在tmux会话中按 `Ctrl+C`，或者：

```bash
tmux kill-session -t trading_bot
```

## 查看日志

日志文件保存在 `logs/` 目录：

```bash
# 查看最新的日志
ls -lt logs/ | head -5

# 实时查看日志
tail -f logs/trading_bot_*.log
```

## 系统架构

```
┌─────────────────┐
│  MarketData     │
│  Collector      │───┐
└─────────────────┘   │
                      │
┌─────────────────┐   │    ┌──────────────┐
│   Agent 1       │───┼───▶│  MessageBus  │
│  (50% 本金)     │   │    └──────────────┘
└─────────────────┘   │           │
                      │           │
┌─────────────────┐   │           ▼
│   Agent 2       │───┼───▶┌──────────────┐
│  (50% 本金)     │   │    │   Enhanced    │
└─────────────────┘   │    │   Executor    │
                      │    │               │
                      │    │  ┌──────────┐ │
                      └────┼─▶│  Roostoo  │ │
                           │  │   API    │ │
                           │  └──────────┘ │
                           └───────────────┘
```

## 关键修改

### 1. 全局决策频率限制

- 修改了 `utils/rate_limiter.py`，添加了 `GLOBAL_DECISION_RATE_LIMITER`
- 修改了 `api/agents/base_agent.py`，使用全局限制器
- 确保整个bot在一分钟内最多输出5次决策

### 2. 资本管理

- 使用 `CapitalManager` 管理初始资金
- 两个Agent平分本金（各50%）
- 每个Agent独立操作，互不干扰

### 3. 交易执行

- 使用 `EnhancedTradeExecutor` 执行交易
- 支持资本管理器，确保每个Agent不超过分配的资金
- 真实交易模式（可通过 `DRY_RUN=false` 设置）

## 运行参数

可以通过环境变量控制运行模式：

```bash
# 测试模式（不会真正下单）
export DRY_RUN=true
python run_bot.py

# 真实交易模式（会真正下单）
export DRY_RUN=false
python run_bot.py
```

## 故障排查

### 问题：401 Unauthorized错误

✅ **已修复**：已按照Roostoo官方示例格式修复了API调用代码，确保：
- 时间戳格式正确（13位毫秒级）
- 签名生成正确
- GET请求使用 `params` 参数
- POST请求使用 `data` 参数

### 问题：bot无法启动

1. 检查Python版本：`python --version`（需要3.7+）
2. 检查依赖：`pip list | grep requests`
3. 检查配置：确保 `.env` 文件配置正确

### 问题：决策频率超过限制

系统已自动处理：
- 如果超过每分钟1次的限制，决策会被跳过
- 日志中会显示 "全局决策频率限制: 需要等待 X 秒"

## 更多信息

- 详细运行指南：`TMUX_RUN_GUIDE.md`
- API修复说明：查看之前的修复记录

