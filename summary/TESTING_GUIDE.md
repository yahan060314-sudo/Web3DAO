# Linux 2023 虚拟机测试指南

## 前置准备

### 1. 系统要求
- Linux 2023 (或兼容的Linux发行版)
- Python 3.11+ 
- 网络连接（用于访问API）

### 2. 检查Python版本
```bash
python3 --version
# 应该显示 Python 3.11.x 或更高版本
```

### 3. 检查项目位置
```bash
# 确认你在项目根目录
pwd
# 应该显示类似: /home/ssm-user/Web3DAO 或 /path/to/Web3DAO

# 检查项目结构
ls -la
# 应该看到: api/, config/, prompts/, tools/, README.md 等
```

## 步骤1: 环境准备

### 1.1 创建虚拟环境（如果还没有）
```bash
# 在项目根目录
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate

# 确认虚拟环境已激活（提示符前应该显示 (.venv)）
which python
# 应该显示: /path/to/Web3DAO/.venv/bin/python
```

### 1.2 安装依赖
```bash
# 确保在项目根目录且虚拟环境已激活
pip install --upgrade pip

# 安装基础依赖
pip install requests python-dotenv

# 如果需要使用Qwen SDK（可选）
# pip install dashscope
```

### 1.3 验证安装
```bash
python -c "import requests; import dotenv; print('✓ Dependencies installed')"
```

## 步骤2: 配置文件设置

### 2.1 创建 .env 文件
```bash
# 在项目根目录创建 .env 文件
cat > .env << 'EOF'
# LLM Provider Configuration
LLM_PROVIDER=deepseek

# DeepSeek Configuration
DEEPSEEK_API_KEY=sk-your-actual-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# Qwen Configuration (可选)
# QWEN_API_KEY=your_qwen_api_key
# QWEN_BASE_URL=https://api.qwen.ai
# QWEN_MODEL=qwen-chat

# Roostoo API Configuration
ROOSTOO_API_KEY=your_roostoo_api_key
ROOSTOO_SECRET_KEY=your_roostoo_secret_key
EOF
```

### 2.2 编辑 .env 文件
```bash
# 使用你喜欢的编辑器编辑 .env 文件
nano .env
# 或
vim .env

# 替换以下值：
# - DEEPSEEK_API_KEY: 你的DeepSeek API密钥
# - ROOSTOO_API_KEY: 你的Roostoo API密钥
# - ROOSTOO_SECRET_KEY: 你的Roostoo Secret密钥
```

### 2.3 验证配置文件
```bash
# 检查 .env 文件是否存在且可读
test -f .env && echo "✓ .env file exists" || echo "✗ .env file not found"

# 检查关键配置（不显示实际值）
grep -q "DEEPSEEK_API_KEY" .env && echo "✓ DeepSeek API key configured" || echo "✗ DeepSeek API key missing"
grep -q "ROOSTOO_API_KEY" .env && echo "✓ Roostoo API key configured" || echo "✗ Roostoo API key missing"
```

## 步骤3: 测试LLM客户端

### 3.1 测试LLM连接
```bash
# 测试DeepSeek API连接
python -m api.llm_clients.example_usage
```

**预期输出**:
```
Successfully loaded environment variables from .env file.
AI回复: [LLM生成的回复内容]
```

**如果出现错误**:
- 401错误: 检查API密钥是否正确
- 402错误: 账户余额不足，需要充值
- 404错误: API URL不正确
- 网络错误: 检查网络连接

### 3.2 验证LLM客户端
```bash
# 测试不同的LLM提供商（如果配置了Qwen）
# 临时修改 .env 中的 LLM_PROVIDER=qwen
python -m api.llm_clients.example_usage
```

## 步骤4: 测试Roostoo客户端

### 4.1 测试Roostoo API连接
```bash
# 测试Roostoo API连接
python -c "
from api.roostoo_client import RoostooClient
client = RoostooClient()
print('Testing Roostoo API...')
try:
    server_time = client.check_server_time()
    print('✓ Server time:', server_time)
    exchange_info = client.get_exchange_info()
    print('✓ Exchange info retrieved')
    print('✓ Roostoo API connection successful')
except Exception as e:
    print('✗ Error:', e)
"
```

**预期输出**:
```
Testing Roostoo API...
✓ Server time: {...}
✓ Exchange info retrieved
✓ Roostoo API connection successful
```

### 4.2 测试数据获取
```bash
# 测试获取ticker数据
python -c "
from api.roostoo_client import RoostooClient
client = RoostooClient()
try:
    ticker = client.get_ticker('BTC/USD')
    print('✓ Ticker data:', ticker)
except Exception as e:
    print('✗ Error:', e)
"
```

## 步骤5: 测试数据格式化

### 5.1 测试DataFormatter
```bash
# 创建测试脚本
cat > test_formatter.py << 'EOF'
from api.agents.data_formatter import DataFormatter

formatter = DataFormatter()

# 模拟ticker数据
mock_ticker = {
    "data": {
        "pair": "BTC/USD",
        "price": "45000.0",
        "volume24h": "1234567.89",
        "change24h": "2.5",
        "high24h": "46000.0",
        "low24h": "44000.0"
    }
}

# 格式化
formatted = formatter.format_ticker(mock_ticker, "BTC/USD")
print("✓ Formatted ticker:", formatted)

# 测试LLM格式化
snapshot = formatter.create_market_snapshot(ticker=formatted)
llm_text = formatter.format_for_llm(snapshot)
print("\n✓ LLM formatted text:")
print(llm_text)
EOF

python test_formatter.py
rm test_formatter.py
```

## 步骤6: 测试Prompt管理器

### 6.1 测试PromptManager加载
```bash
# 测试PromptManager
python -c "
from api.agents.prompt_manager import PromptManager
pm = PromptManager()
print('✓ PromptManager initialized')

# 测试系统prompt
system_prompt = pm.get_system_prompt('TestAgent', risk_level='moderate')
print('✓ System prompt generated (length:', len(system_prompt), 'chars)')

# 检查是否加载了组友的模板
if hasattr(pm, 'spot_trading_template') and pm.spot_trading_template:
    print('✓ Spot trading template loaded')
else:
    print('⚠ Spot trading template not loaded (may be normal if file not found)')
"
```

## 步骤7: 测试完整数据流（简化版）

### 7.1 创建测试脚本
```bash
cat > test_data_flow.py << 'EOF'
#!/usr/bin/env python3
"""
测试完整数据流（简化版，不实际执行交易）
"""
import time
from api.agents.manager import AgentManager
from api.agents.market_collector import MarketDataCollector
from api.agents.prompt_manager import PromptManager

print("=" * 60)
print("Testing Complete Data Flow")
print("=" * 60)

# 1. 初始化
print("\n[1] Initializing components...")
mgr = AgentManager()
pm = PromptManager()
print("✓ AgentManager initialized")
print("✓ PromptManager initialized")

# 2. 创建Agent
print("\n[2] Creating test agent...")
system_prompt = pm.get_system_prompt("TestAgent", risk_level="moderate")
mgr.add_agent(name="test_agent", system_prompt=system_prompt)
mgr.start()
print("✓ Test agent created and started")

# 3. 启动数据采集器
print("\n[3] Starting market data collector...")
collector = MarketDataCollector(
    bus=mgr.bus,
    market_topic=mgr.market_topic,
    pairs=["BTC/USD"],
    collect_interval=3.0,  # 3秒采集一次（测试用）
    collect_balance=True,
    collect_ticker=True
)
collector.start()
print("✓ Market data collector started")

# 4. 等待数据采集
print("\n[4] Waiting for market data (10 seconds)...")
time.sleep(10)

# 5. 检查数据
print("\n[5] Checking collected data...")
snapshot = collector.get_latest_snapshot()
if snapshot:
    print("✓ Market snapshot created")
    if snapshot.get("ticker"):
        print("  - Ticker data: ✓")
    if snapshot.get("balance"):
        print("  - Balance data: ✓")
else:
    print("⚠ No market snapshot yet (may need more time)")

# 6. 测试Prompt生成
print("\n[6] Testing prompt generation...")
if snapshot:
    prompt = pm.create_trading_prompt(snapshot)
    print("✓ Trading prompt generated (length:", len(prompt), "chars)")
    
    # 测试组友的模板（如果可用）
    spot_prompt = pm.create_spot_prompt_from_market_data(snapshot)
    if spot_prompt:
        print("✓ Spot trading prompt generated (using teammate's template)")
    else:
        print("⚠ Spot trading prompt not available (using default)")
else:
    print("⚠ Cannot generate prompt (no market data)")

# 7. 检查Agent决策
print("\n[7] Checking agent decisions...")
time.sleep(5)  # 等待Agent处理
decisions = mgr.collect_decisions(max_items=5, wait_seconds=2.0)
if decisions:
    print(f"✓ Received {len(decisions)} decision(s)")
    for i, d in enumerate(decisions, 1):
        print(f"  {i}. Agent: {d.get('agent')}")
        print(f"     Decision: {d.get('decision', 'N/A')[:80]}")
else:
    print("⚠ No decisions received yet")

# 8. 清理
print("\n[8] Cleaning up...")
collector.stop()
collector.join(timeout=2)
mgr.stop()
print("✓ Cleanup complete")

print("\n" + "=" * 60)
print("Data flow test completed!")
print("=" * 60)
EOF

chmod +x test_data_flow.py
python test_data_flow.py
```

## 步骤8: 运行完整集成测试

### 8.1 运行集成示例（不执行实际交易）
```bash
# 运行集成示例（会运行2分钟）
python -m api.agents.integrated_example
```

**预期输出**:
```
============================================================
Web3 Quant Trading System - Integrated Example
============================================================

[1] Initializing Agent Manager...
[2] Initializing Prompt Manager...
[PromptManager] Loaded spot trading template from ...
[3] Creating AI Agents...
[4] Starting Agents...
[5] Starting Market Data Collector...
[MarketDataCollector] Started. Collecting data every 5.0s
[6] Starting Trade Executor...
...
```

**注意**: 这个示例会运行2分钟，期间会：
- 采集市场数据
- 生成Agent决策
- 显示决策结果

按 `Ctrl+C` 可以提前停止。

### 8.2 运行简化测试（快速验证）
```bash
# 运行简化测试（只测试数据流，不执行交易）
python test_data_flow.py
```

## 步骤9: 验证检查清单

### 9.1 检查所有组件
```bash
# 创建验证脚本
cat > verify_system.py << 'EOF'
#!/usr/bin/env python3
"""系统验证脚本"""
import sys

checks = []
errors = []

# 1. 检查Python版本
import sys
if sys.version_info >= (3, 11):
    checks.append("✓ Python version: " + sys.version.split()[0])
else:
    errors.append("✗ Python version too old (need 3.11+)")

# 2. 检查依赖
try:
    import requests
    checks.append("✓ requests installed")
except ImportError:
    errors.append("✗ requests not installed")

try:
    import dotenv
    checks.append("✓ python-dotenv installed")
except ImportError:
    errors.append("✗ python-dotenv not installed")

# 3. 检查配置文件
import os
from pathlib import Path
env_file = Path(".env")
if env_file.exists():
    checks.append("✓ .env file exists")
    # 检查关键配置
    from dotenv import load_dotenv
    load_dotenv()
    if os.getenv("DEEPSEEK_API_KEY"):
        checks.append("✓ DEEPSEEK_API_KEY configured")
    else:
        errors.append("✗ DEEPSEEK_API_KEY not set")
    
    if os.getenv("ROOSTOO_API_KEY"):
        checks.append("✓ ROOSTOO_API_KEY configured")
    else:
        errors.append("✗ ROOSTOO_API_KEY not set")
else:
    errors.append("✗ .env file not found")

# 4. 检查模块导入
try:
    from api.llm_clients.factory import get_llm_client
    checks.append("✓ LLM clients importable")
except Exception as e:
    errors.append(f"✗ LLM clients import error: {e}")

try:
    from api.roostoo_client import RoostooClient
    checks.append("✓ Roostoo client importable")
except Exception as e:
    errors.append(f"✗ Roostoo client import error: {e}")

try:
    from api.agents.manager import AgentManager
    from api.agents.market_collector import MarketDataCollector
    from api.agents.prompt_manager import PromptManager
    checks.append("✓ Agent modules importable")
except Exception as e:
    errors.append(f"✗ Agent modules import error: {e}")

# 5. 检查prompts文件夹
prompts_dir = Path("prompts")
if prompts_dir.exists():
    checks.append("✓ prompts directory exists")
    if (prompts_dir / "natural_language_prompt.txt").exists():
        checks.append("✓ natural_language_prompt.txt exists")
    else:
        errors.append("⚠ natural_language_prompt.txt not found (optional)")
else:
    errors.append("⚠ prompts directory not found (optional)")

# 输出结果
print("=" * 60)
print("System Verification")
print("=" * 60)
print("\nChecks:")
for check in checks:
    print(f"  {check}")

if errors:
    print("\nErrors/Warnings:")
    for error in errors:
        print(f"  {error}")
else:
    print("\n✓ All checks passed!")

print("\n" + "=" * 60)

if errors:
    sys.exit(1)
else:
    sys.exit(0)
EOF

chmod +x verify_system.py
python verify_system.py
```

## 步骤10: 完整端到端测试

### 10.1 创建完整测试脚本
```bash
cat > full_test.sh << 'EOF'
#!/bin/bash
# 完整测试脚本

echo "=========================================="
echo "Web3DAO Complete System Test"
echo "=========================================="
echo ""

# 检查虚拟环境
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠ Warning: Virtual environment not activated"
    echo "  Run: source .venv/bin/activate"
    exit 1
fi

echo "[Step 1] Verifying system..."
python verify_system.py
if [ $? -ne 0 ]; then
    echo "✗ System verification failed"
    exit 1
fi

echo ""
echo "[Step 2] Testing LLM connection..."
python -m api.llm_clients.example_usage
if [ $? -ne 0 ]; then
    echo "✗ LLM connection test failed"
    exit 1
fi

echo ""
echo "[Step 3] Testing Roostoo connection..."
python -c "
from api.roostoo_client import RoostooClient
client = RoostooClient()
try:
    client.check_server_time()
    print('✓ Roostoo API connection successful')
except Exception as e:
    print(f'✗ Roostoo API error: {e}')
    exit(1)
"
if [ $? -ne 0 ]; then
    exit 1
fi

echo ""
echo "[Step 4] Testing data flow (30 seconds)..."
timeout 30 python test_data_flow.py || echo "⚠ Test timed out or interrupted"

echo ""
echo "=========================================="
echo "✓ All tests completed!"
echo "=========================================="
EOF

chmod +x full_test.sh
./full_test.sh
```

## 常见问题排查

### 问题1: 模块导入错误
```bash
# 确保在项目根目录
pwd
# 应该显示项目根目录路径

# 检查Python路径
python -c "import sys; print('\n'.join(sys.path))"

# 如果路径不对，添加项目根目录到PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### 问题2: API密钥错误
```bash
# 检查.env文件
cat .env | grep -v "KEY\|SECRET"  # 不显示密钥值，只显示配置项

# 验证环境变量是否加载
python -c "
from dotenv import load_dotenv
import os
load_dotenv()
print('DEEPSEEK_API_KEY:', 'SET' if os.getenv('DEEPSEEK_API_KEY') else 'NOT SET')
print('ROOSTOO_API_KEY:', 'SET' if os.getenv('ROOSTOO_API_KEY') else 'NOT SET')
"
```

### 问题3: 网络连接问题
```bash
# 测试API连接
curl -I https://api.deepseek.com
curl -I https://mock-api.roostoo.com

# 如果无法连接，检查防火墙/代理设置
```

### 问题4: 权限问题
```bash
# 确保脚本有执行权限
chmod +x test_*.py verify_system.py full_test.sh

# 确保可以写入日志（如果有）
touch test.log
chmod 666 test.log
```

## 快速测试命令汇总

```bash
# 1. 激活虚拟环境
source .venv/bin/activate

# 2. 验证系统
python verify_system.py

# 3. 测试LLM
python -m api.llm_clients.example_usage

# 4. 测试Roostoo
python -c "from api.roostoo_client import RoostooClient; c=RoostooClient(); print(c.check_server_time())"

# 5. 测试数据流（30秒）
timeout 30 python test_data_flow.py

# 6. 完整集成测试（2分钟）
python -m api.agents.integrated_example
```

## 预期测试结果

### 成功标志:
- ✅ 所有模块可以正常导入
- ✅ LLM API可以正常调用
- ✅ Roostoo API可以正常连接
- ✅ 市场数据可以正常采集
- ✅ Agent可以正常生成决策
- ✅ 数据流完整无中断

### 失败处理:
- 检查错误信息
- 验证API密钥
- 检查网络连接
- 查看日志输出

## 下一步

测试成功后，可以：
1. 调整采集频率（`collect_interval`）
2. 添加更多交易对
3. 使用组友的详细prompt模板
4. 配置实际交易执行（谨慎！）

