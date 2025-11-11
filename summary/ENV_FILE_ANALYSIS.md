# .env文件加载详细分析

## 📋 问题说明

在虚拟机上有两个环境文件：
- `.env` - 可能是旧的或不完整的配置
- `.env.save` - 可能是正确的配置

需要确定代码实际使用的是哪个文件。

## 🔍 代码中所有加载.env文件的位置

### 1. `config/credentials.py` - 明确指定`.env`路径

**代码位置**: `config/credentials.py` 第9-14行

```python
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(project_root, '.env')

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    print("Successfully loaded environment variables from .env file.")
```

**行为**:
- ✅ **明确指定使用项目根目录下的`.env`文件**
- ✅ 如果`.env`不存在，会打印警告，但不会加载`.env.save`
- ❌ **不会加载`.env.save`**

**使用场景**: 如果代码中导入了`config.credentials`，会使用这个加载方式

### 2. `api/roostoo_client.py` - 默认加载

**代码位置**: `api/roostoo_client.py` 第16-17行

```python
from dotenv import load_dotenv
load_dotenv()
```

**行为**:
- ⚠️ **使用`load_dotenv()`的默认行为**
- ⚠️ 默认会在**当前工作目录**查找`.env`文件
- ❌ **不会加载`.env.save`**

**关键点**: 
- 如果从项目根目录运行，会加载项目根目录的`.env`
- 如果从其他目录运行，会在那个目录查找`.env`

### 3. `config/config.py` - 默认加载

**代码位置**: `config/config.py` 第4-7行

```python
from dotenv import load_dotenv
load_dotenv()
```

**行为**:
- ⚠️ **使用`load_dotenv()`的默认行为**
- ⚠️ 默认会在**当前工作目录**查找`.env`文件
- ❌ **不会加载`.env.save`**

### 4. `api/llm_clients/factory.py` - 向上查找`.env`

**代码位置**: `api/llm_clients/factory.py` 第13-23行

```python
def _load_dotenv_once():
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        candidate = os.path.join(here, '.env')
        if os.path.exists(candidate):
            load_dotenv(dotenv_path=candidate)
            return
        here = os.path.dirname(here)
    load_dotenv()  # 兜底：尝试默认加载
```

**行为**:
- ✅ **从当前文件位置向上查找`.env`文件，最多查找5层**
- ✅ 如果找到`.env`，就加载它
- ❌ **不会加载`.env.save`**

**关键点**: 
- 会从`api/llm_clients/`目录开始向上查找
- 最终会找到项目根目录的`.env`

### 5. `test_real_api.py` - 默认加载

**代码位置**: `test_real_api.py` 第15-16行

```python
from dotenv import load_dotenv
load_dotenv()
```

**行为**:
- ⚠️ **使用`load_dotenv()`的默认行为**
- ⚠️ 默认会在**当前工作目录**查找`.env`文件
- ❌ **不会加载`.env.save`**

### 6. `diagnose_system.py` - 默认加载

**代码位置**: `diagnose_system.py` 第13-14行

```python
from dotenv import load_dotenv
load_dotenv()
```

**行为**:
- ⚠️ **使用`load_dotenv()`的默认行为**
- ⚠️ 默认会在**当前工作目录**查找`.env`文件
- ❌ **不会加载`.env.save`**

### 7. 其他文件

- `tools/main.py` - 使用`load_dotenv()`（默认行为）
- `prompts/agent_prompt.py` - 使用`load_dotenv()`（默认行为）
- `test_complete_system.py` - 使用`load_dotenv()`（默认行为）
- `test_decision_to_market.py` - 使用`load_dotenv()`（默认行为）

## 🎯 关键发现

### 1. 所有代码都只加载`.env`文件

**重要结论**: 
- ✅ **所有代码都只查找和加载`.env`文件**
- ❌ **没有任何代码会加载`.env.save`文件**

### 2. `load_dotenv()`的默认行为

**默认行为**:
- 在**当前工作目录**查找`.env`文件
- 如果从项目根目录运行，会加载项目根目录的`.env`
- **不会自动查找`.env.save`或其他变体**

### 3. 为什么代码能正常运行？

**可能的原因**:

1. **`.env`文件存在且包含正确的配置**
   - 即使`.env.save`有更完整的配置，如果`.env`也有必要的配置，代码就能运行

2. **环境变量已通过其他方式设置**
   - 系统环境变量
   - Shell配置文件（`.bashrc`, `.zshrc`等）
   - 其他脚本设置的环境变量

3. **代码使用了默认值**
   - 某些配置项有默认值，即使`.env`中没有，也能运行

## 🔧 如何确认实际使用的文件

### 方法1: 检查当前工作目录的`.env`文件

```bash
# 在项目根目录运行
pwd
ls -la .env .env.save

# 检查.env文件内容
cat .env

# 检查.env.save文件内容
cat .env.save
```

### 方法2: 在代码中添加调试信息

创建一个测试脚本：

```python
import os
from pathlib import Path
from dotenv import load_dotenv

# 记录当前工作目录
cwd = os.getcwd()
print(f"当前工作目录: {cwd}")

# 检查.env文件
env_file = Path(".env")
env_save_file = Path(".env.save")

print(f"\n.env文件:")
print(f"  存在: {env_file.exists()}")
if env_file.exists():
    print(f"  路径: {env_file.absolute()}")
    print(f"  大小: {env_file.stat().st_size} bytes")

print(f"\n.env.save文件:")
print(f"  存在: {env_save_file.exists()}")
if env_save_file.exists():
    print(f"  路径: {env_save_file.absolute()}")
    print(f"  大小: {env_save_file.stat().st_size} bytes")

# 加载.env
print(f"\n加载.env文件...")
load_dotenv()

# 检查加载的环境变量
print(f"\n加载的环境变量:")
print(f"  ROOSTOO_API_URL: {os.getenv('ROOSTOO_API_URL', 'NOT SET')}")
print(f"  ROOSTOO_API_KEY: {os.getenv('ROOSTOO_API_KEY', 'NOT SET')[:20]}..." if os.getenv('ROOSTOO_API_KEY') else "  ROOSTOO_API_KEY: NOT SET")
print(f"  LLM_PROVIDER: {os.getenv('LLM_PROVIDER', 'NOT SET')}")
```

### 方法3: 使用Python检查

```bash
python -c "
import os
from pathlib import Path
from dotenv import load_dotenv

cwd = os.getcwd()
print(f'当前工作目录: {cwd}')

env_file = Path('.env')
env_save_file = Path('.env.save')

print(f'\n.env文件存在: {env_file.exists()}')
print(f'.env.save文件存在: {env_save_file.exists()}')

if env_file.exists():
    print(f'\n.env文件路径: {env_file.absolute()}')
    
load_dotenv()
print(f'\nROOSTOO_API_URL: {os.getenv(\"ROOSTOO_API_URL\", \"NOT SET\")}')
"
```

## 💡 解决方案

### 方案1: 将`.env.save`的内容复制到`.env`

```bash
# 备份当前的.env
cp .env .env.backup

# 将.env.save的内容复制到.env
cp .env.save .env

# 验证
cat .env
```

### 方案2: 重命名文件

```bash
# 备份当前的.env
cp .env .env.old

# 将.env.save重命名为.env
mv .env.save .env

# 验证
ls -la .env
```

### 方案3: 修改代码以支持`.env.save`

**不推荐**，因为需要修改多个文件。

如果确实需要，可以创建一个统一的加载函数：

```python
# config/env_loader.py
import os
from pathlib import Path
from dotenv import load_dotenv

def load_env_file():
    """加载环境变量，优先使用.env，如果不存在则使用.env.save"""
    project_root = Path(__file__).parent.parent
    env_file = project_root / '.env'
    env_save_file = project_root / '.env.save'
    
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)
        print(f"Loaded environment variables from: {env_file}")
    elif env_save_file.exists():
        load_dotenv(dotenv_path=env_save_file)
        print(f"Loaded environment variables from: {env_save_file}")
    else:
        load_dotenv()  # 默认行为
        print("Using default .env loading behavior")
```

然后在所有需要的地方导入这个函数。

## 📊 总结

### 关键结论

1. ✅ **所有代码都只加载`.env`文件，不会加载`.env.save`**

2. ✅ **`load_dotenv()`的默认行为**:
   - 在当前工作目录查找`.env`文件
   - 如果从项目根目录运行，会加载项目根目录的`.env`

3. ⚠️ **如果代码能正常运行，说明**:
   - `.env`文件存在且包含必要的配置
   - 或者环境变量通过其他方式设置

4. 💡 **建议**:
   - 将`.env.save`的内容合并到`.env`
   - 或者将`.env.save`重命名为`.env`（先备份当前的`.env`）

### 快速检查命令

```bash
# 1. 检查两个文件是否存在
ls -la .env .env.save

# 2. 比较两个文件的内容
diff .env .env.save

# 3. 检查当前使用的配置
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('ROOSTOO_API_URL:', os.getenv('ROOSTOO_API_URL', 'NOT SET'))"
```

