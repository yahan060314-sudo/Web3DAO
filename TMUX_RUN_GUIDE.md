# Tmux运行指南

## 快速开始

### 1. 创建tmux会话并运行bot

```bash
cd /path/to/Web3DAO
tmux new-session -d -s trading_bot 'python run_bot.py'
```

### 2. 查看运行状态

```bash
tmux attach -t trading_bot
```

### 3. 停止运行

在tmux会话中按 `Ctrl+C`，或者：

```bash
tmux kill-session -t trading_bot
```

## 常用tmux命令

### 会话管理

```bash
# 列出所有会话
tmux ls

# 创建新会话
tmux new-session -d -s session_name 'command'

# 附加到会话
tmux attach -t session_name

# 分离会话（在会话内按 Ctrl+B 然后按 D）
# 或者直接关闭终端窗口，会话会继续运行

# 杀死会话
tmux kill-session -t session_name

# 杀死所有会话
tmux kill-server
```

### 窗口和面板

```bash
# 在会话内：
# Ctrl+B 然后按 C - 创建新窗口
# Ctrl+B 然后按 N - 下一个窗口
# Ctrl+B 然后按 P - 上一个窗口
# Ctrl+B 然后按 % - 垂直分割面板
# Ctrl+B 然后按 " - 水平分割面板
# Ctrl+B 然后按方向键 - 切换面板
```

## 运行bot的完整流程

### 1. 确保环境配置正确

检查 `.env` 文件是否包含所有必要的配置：

```bash
cat .env
```

必须包含：
- `ROOSTOO_API_KEY`
- `ROOSTOO_SECRET_KEY`
- `ROOSTOO_API_URL`
- 至少一个LLM API KEY (`DEEPSEEK_API_KEY` / `QWEN_API_KEY` / `MINIMAX_API_KEY`)

### 2. 在tmux中运行

```bash
# 进入项目目录
cd /path/to/Web3DAO

# 创建tmux会话并运行bot
tmux new-session -d -s trading_bot 'python run_bot.py'

# 查看运行状态
tmux attach -t trading_bot
```

### 3. 查看日志

日志文件保存在 `logs/` 目录下：

```bash
# 查看最新的日志文件
ls -lt logs/ | head -5

# 实时查看日志
tail -f logs/trading_bot_*.log
```

### 4. 检查运行状态

```bash
# 查看进程
ps aux | grep run_bot.py

# 查看tmux会话
tmux ls
```

## 系统要求

- Python 3.7+
- 所有依赖包已安装（通过 `pip install -r requirements.txt`）
- `.env` 文件配置正确
- tmux已安装（Linux 2023通常已预装）

## 注意事项

1. **持续运行**: bot会在tmux会话中持续运行，即使你断开SSH连接也不会停止
2. **日志记录**: 所有日志都会保存到 `logs/` 目录，方便后续分析
3. **优雅关闭**: 使用 `Ctrl+C` 或 `tmux kill-session` 可以优雅关闭bot
4. **资源监控**: 建议定期检查系统资源使用情况

## 故障排查

### bot无法启动

1. 检查Python环境：
   ```bash
   python --version
   ```

2. 检查依赖：
   ```bash
   pip list | grep -E "requests|dotenv|hmac"
   ```

3. 检查配置文件：
   ```bash
   python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('API_KEY:', bool(os.getenv('ROOSTOO_API_KEY')))"
   ```

### bot运行中出错

1. 查看日志文件：
   ```bash
   tail -100 logs/trading_bot_*.log
   ```

2. 重新附加到tmux会话查看实时输出：
   ```bash
   tmux attach -t trading_bot
   ```

### 停止bot后无法重新启动

1. 检查是否有残留进程：
   ```bash
   ps aux | grep run_bot.py
   ```

2. 如果有残留进程，杀死它们：
   ```bash
   pkill -f run_bot.py
   ```

3. 检查tmux会话：
   ```bash
   tmux ls
   ```

4. 如果有残留会话，杀死它：
   ```bash
   tmux kill-session -t trading_bot
   ```

## 系统特性

- ✅ 两个Agent平分本金，各自独立操作
- ✅ 全局决策频率限制：每分钟最多5次
- ✅ API调用频率限制：每分钟最多5次
- ✅ 决策通过API正确传到市场
- ✅ 完整的日志记录
- ✅ 优雅的信号处理
- ✅ 适合在tmux中持续运行

