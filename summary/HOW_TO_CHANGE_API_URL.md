# 如何将模拟 API URL 改成真实 URL

## 📝 步骤说明

### 方法1: 使用文本编辑器（推荐）

#### 步骤1: 创建或编辑 .env 文件

在项目根目录（`/Users/snowman/Documents/GitHub/Web3DAO/`）创建或编辑 `.env` 文件。

**使用终端**:
```bash
cd /Users/snowman/Documents/GitHub/Web3DAO
nano .env
# 或
vim .env
# 或
code .env  # 如果使用 VS Code
```

**使用 Finder** (macOS):
1. 打开 Finder
2. 导航到 `/Users/snowman/Documents/GitHub/Web3DAO/`
3. 按 `Cmd + Shift + .` 显示隐藏文件
4. 找到 `.env` 文件（如果不存在，创建一个新文件）
5. 用文本编辑器打开

#### 步骤2: 添加或修改配置

在 `.env` 文件中添加或修改以下内容：

```env
# Roostoo API Configuration
ROOSTOO_API_KEY=K9IL3ZxCV1bN5mQwE7rT0yUiP2oA8sDdF6gJ1hKIZ4xC9vBnM0qW3eRtY5ul7oPa
ROOSTOO_SECRET_KEY=cV2bN4mQwE6rT8yUiP0oA2sDdF4gJ6hKIZ8xC0vBnM2qW4eRtY6ul0oPaS2d

# 真实 API URL (重要！)
ROOSTOO_API_URL=https://api.roostoo.com
```

**关键点**:
- `ROOSTOO_API_URL` 这一行决定使用哪个 API
- 如果设置为 `https://mock-api.roostoo.com`，使用模拟API
- 如果设置为 `https://api.roostoo.com`，使用真实API
- 如果这一行不存在，默认使用模拟API

#### 步骤3: 保存文件

保存 `.env` 文件（在 nano 中按 `Ctrl+X`，然后 `Y`，然后 `Enter`）

---

### 方法2: 使用命令行（快速）

#### 步骤1: 创建 .env 文件（如果不存在）

```bash
cd /Users/snowman/Documents/GitHub/Web3DAO
touch .env
```

#### 步骤2: 添加配置

```bash
cat >> .env << 'EOF'
# Roostoo API Configuration
ROOSTOO_API_KEY=K9IL3ZxCV1bN5mQwE7rT0yUiP2oA8sDdF6gJ1hKIZ4xC9vBnM0qW3eRtY5ul7oPa
ROOSTOO_SECRET_KEY=cV2bN4mQwE6rT8yUiP0oA2sDdF4gJ6hKIZ8xC0vBnM2qW4eRtY6ul0oPaS2d
ROOSTOO_API_URL=https://api.roostoo.com
EOF
```

#### 步骤3: 验证配置

```bash
cat .env
```

---

## 🔍 验证更改是否生效

### 方法1: 运行测试脚本

```bash
python test_real_api.py
```

**预期输出**:
```
[RoostooClient] ✓ 使用真实API: https://api.roostoo.com
API URL: https://api.roostoo.com
Connection: {'ServerTime': ...}
```

### 方法2: 快速测试

```bash
python -c "from api.roostoo_client import RoostooClient; client = RoostooClient(); print(f'API URL: {client.base_url}')"
```

**预期输出**:
```
[RoostooClient] ✓ 使用真实API: https://api.roostoo.com
API URL: https://api.roostoo.com
```

---

## 📋 .env 文件完整示例

```env
# =============================================================================
# Roostoo API Configuration (Official Competition)
# =============================================================================
# 比赛从 2025年11月10日 晚上8点 HKT 开始

# API Credentials
ROOSTOO_API_KEY=K9IL3ZxCV1bN5mQwE7rT0yUiP2oA8sDdF6gJ1hKIZ4xC9vBnM0qW3eRtY5ul7oPa
ROOSTOO_SECRET_KEY=cV2bN4mQwE6rT8yUiP0oA2sDdF4gJ6hKIZ8xC0vBnM2qW4eRtY6ul0oPaS2d

# API URL
# 模拟API (测试环境): https://mock-api.roostoo.com
# 真实API (生产环境): https://api.roostoo.com
ROOSTOO_API_URL=https://api.roostoo.com

# =============================================================================
# LLM Configuration
# =============================================================================

# DeepSeek
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# LLM Provider Selection
LLM_PROVIDER=deepseek
```

---

## 🔄 切换 API URL

### 切换到真实API

在 `.env` 文件中设置：
```env
ROOSTOO_API_URL=https://api.roostoo.com
```

### 切换回模拟API

在 `.env` 文件中设置：
```env
ROOSTOO_API_URL=https://mock-api.roostoo.com
```

### 临时使用不同的API URL

在代码中直接指定：
```python
from api.roostoo_client import RoostooClient

# 使用真实API
client = RoostooClient(base_url="https://api.roostoo.com")

# 或使用模拟API
client = RoostooClient(base_url="https://mock-api.roostoo.com")
```

---

## ⚠️ 注意事项

### 1. .env 文件位置

确保 `.env` 文件在项目根目录：
```
/Users/snowman/Documents/GitHub/Web3DAO/.env
```

### 2. 文件格式

- 每行一个配置项
- 格式：`KEY=value`
- 不要有多余的空格
- 不要在值两边加引号（除非值本身包含引号）

### 3. 环境变量优先级

1. 代码中直接指定的参数（最高优先级）
2. `.env` 文件中的配置
3. 系统环境变量
4. 代码中的默认值（最低优先级）

### 4. 重启程序

修改 `.env` 文件后，需要重新运行程序才能生效。

---

## 🧪 测试步骤

### 步骤1: 创建/编辑 .env 文件

```bash
cd /Users/snowman/Documents/GitHub/Web3DAO
nano .env
```

### 步骤2: 添加配置

```env
ROOSTOO_API_KEY=K9IL3ZxCV1bN5mQwE7rT0yUiP2oA8sDdF6gJ1hKIZ4xC9vBnM0qW3eRtY5ul7oPa
ROOSTOO_SECRET_KEY=cV2bN4mQwE6rT8yUiP0oA2sDdF4gJ6hKIZ8xC0vBnM2qW4eRtY6ul0oPaS2d
ROOSTOO_API_URL=https://api.roostoo.com
```

### 步骤3: 保存文件

- 在 nano 中：按 `Ctrl+X`，然后 `Y`，然后 `Enter`
- 在 vim 中：按 `Esc`，然后输入 `:wq`，然后 `Enter`
- 在其他编辑器中：保存文件

### 步骤4: 验证配置

```bash
python -c "from api.roostoo_client import RoostooClient; client = RoostooClient(); print(f'API URL: {client.base_url}')"
```

### 步骤5: 测试连接

```bash
python test_real_api.py
```

---

## 🐛 故障排查

### 问题1: .env 文件不存在

**解决方法**:
```bash
cd /Users/snowman/Documents/GitHub/Web3DAO
touch .env
nano .env
```

### 问题2: 配置不生效

**检查**:
1. `.env` 文件是否在项目根目录？
2. 文件格式是否正确？
3. 是否重新运行了程序？

**解决方法**:
```bash
# 检查 .env 文件内容
cat .env

# 检查环境变量是否加载
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('ROOSTOO_API_URL'))"
```

### 问题3: 仍然使用模拟API

**检查**:
1. `ROOSTOO_API_URL` 是否设置正确？
2. 是否有拼写错误？
3. 是否有多余的空格？

**解决方法**:
```bash
# 检查 .env 文件
cat .env | grep ROOSTOO_API_URL

# 应该输出: ROOSTOO_API_URL=https://api.roostoo.com
```

---

## 📞 需要帮助？

如果遇到问题，请检查：

1. ✅ `.env` 文件是否在项目根目录？
2. ✅ 文件格式是否正确？
3. ✅ `ROOSTOO_API_URL` 是否设置正确？
4. ✅ 是否重新运行了程序？

---

## 🎯 快速参考

### 创建 .env 文件
```bash
cd /Users/snowman/Documents/GitHub/Web3DAO
nano .env
```

### 添加配置
```env
ROOSTOO_API_KEY=K9IL3ZxCV1bN5mQwE7rT0yUiP2oA8sDdF6gJ1hKIZ4xC9vBnM0qW3eRtY5ul7oPa
ROOSTOO_SECRET_KEY=cV2bN4mQwE6rT8yUiP0oA2sDdF4gJ6hKIZ8xC0vBnM2qW4eRtY6ul0oPaS2d
ROOSTOO_API_URL=https://api.roostoo.com
```

### 验证配置
```bash
python -c "from api.roostoo_client import RoostooClient; client = RoostooClient(); print(f'API URL: {client.base_url}')"
```

### 测试连接
```bash
python test_real_api.py
```

