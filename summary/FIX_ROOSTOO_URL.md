# 修复 Roostoo API URL 配置

## ✅ 代码已更新

代码中的默认 URL 已经设置为 `https://mock-api.roostoo.com`

## 🔍 检查当前配置

运行以下命令检查当前使用的 URL：

```bash
python check_roostoo_url.py
```

## 🔧 如何修改 .env 文件

如果 `.env` 文件中设置了错误的 URL，请按以下步骤修改：

### 方法1: 使用终端（推荐）

```bash
# 1. 检查当前配置
python check_roostoo_url.py

# 2. 编辑 .env 文件
nano .env
# 或
vim .env
# 或
open -e .env  # macOS

# 3. 找到 ROOSTOO_API_URL 这一行，修改为：
ROOSTOO_API_URL=https://mock-api.roostoo.com

# 4. 保存文件

# 5. 再次检查配置
python check_roostoo_url.py
```

### 方法2: 使用 Finder（macOS）

1. 打开 Finder
2. 导航到项目目录：`/Users/snowman/Documents/GitHub/Web3DAO`
3. 找到 `.env` 文件
4. 右键点击 → "打开方式" → "文本编辑"
5. 找到 `ROOSTOO_API_URL` 这一行
6. 修改为：`ROOSTOO_API_URL=https://mock-api.roostoo.com`
7. 保存文件

### 方法3: 使用命令直接修改

```bash
# 如果 .env 文件中已有 ROOSTOO_API_URL，替换它
sed -i '' 's|ROOSTOO_API_URL=.*|ROOSTOO_API_URL=https://mock-api.roostoo.com|g' .env

# 如果 .env 文件中没有 ROOSTOO_API_URL，添加它
echo "ROOSTOO_API_URL=https://mock-api.roostoo.com" >> .env
```

## 📋 .env 文件示例

确保 `.env` 文件包含以下配置：

```env
# Roostoo API
ROOSTOO_API_KEY=你的API密钥
ROOSTOO_SECRET_KEY=你的Secret密钥
ROOSTOO_API_URL=https://mock-api.roostoo.com

# LLM API
DEEPSEEK_API_KEY=你的DeepSeek API密钥
QWEN_API_KEY=你的Qwen API密钥
LLM_PROVIDER=deepseek
```

## ✅ 验证配置

### 1. 检查 URL 配置

```bash
python check_roostoo_url.py
```

**预期输出**:
```
实际使用的 URL: https://mock-api.roostoo.com
✓ 使用 Mock API (测试环境)
```

### 2. 测试连接

```bash
python diagnose_roostoo_connection.py
```

### 3. 运行测试

```bash
python test_complete_system.py --quick
```

## 🎯 快速修复命令

如果 `.env` 文件中设置了错误的 URL，运行以下命令快速修复：

```bash
# 备份 .env 文件
cp .env .env.backup

# 修改 ROOSTOO_API_URL
sed -i '' 's|^ROOSTOO_API_URL=.*|ROOSTOO_API_URL=https://mock-api.roostoo.com|g' .env

# 验证修改
python check_roostoo_url.py
```

## 📝 注意事项

1. **环境变量优先级**: 
   - 如果 `.env` 文件中设置了 `ROOSTOO_API_URL`，会使用 `.env` 文件中的值
   - 如果 `.env` 文件中没有设置，会使用代码中的默认值 `https://mock-api.roostoo.com`

2. **Mock API vs 真实 API**:
   - Mock API (`https://mock-api.roostoo.com`): 用于测试，不会真正下单
   - 真实 API (`https://api.roostoo.com`): 用于生产，会真正下单

3. **配置文件位置**:
   - `.env` 文件应该在项目根目录
   - `.env` 文件通常被 `.gitignore` 忽略，不会被提交到 Git

## 🔍 故障排查

### 问题1: 仍然使用错误的 URL

**原因**: `.env` 文件中设置了错误的 URL

**解决方案**:
1. 检查 `.env` 文件
2. 修改 `ROOSTOO_API_URL=https://mock-api.roostoo.com`
3. 重新运行测试

### 问题2: 环境变量没有生效

**原因**: 环境变量没有正确加载

**解决方案**:
1. 确认 `.env` 文件在项目根目录
2. 确认 `.env` 文件格式正确
3. 重启 Python 进程

### 问题3: 无法找到 .env 文件

**原因**: `.env` 文件不存在

**解决方案**:
1. 创建 `.env` 文件
2. 添加必要的配置
3. 确保文件在项目根目录

## 🎉 完成

修改完成后，运行测试验证：

```bash
python test_complete_system.py --quick
```

现在应该使用 Mock API (`https://mock-api.roostoo.com`)，不会真正下单。

