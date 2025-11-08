# Linux 2023 虚拟机测试命令汇总

## 快速开始

### 1. 激活虚拟环境
```bash
source .venv/bin/activate
```

### 2. 运行完整测试（推荐）
```bash
# 标准测试（约1分钟）
python test_complete_system.py

# 快速测试（约30秒）
python test_complete_system.py --quick

# 完整测试（约2分钟，包含完整集成）
python test_complete_system.py --full
```

## 详细测试步骤

### 步骤1: 系统验证
```bash
python -c "
import sys
print('Python:', sys.version)
import requests, dotenv
print('✓ Dependencies OK')
"
```

### 步骤2: 测试LLM连接
```bash
python -m api.llm_clients.example_usage
```

### 步骤3: 测试Roostoo连接
```bash
python -c "
from api.roostoo_client import RoostooClient
client = RoostooClient()
print('Server time:', client.check_server_time())
print('Ticker:', client.get_ticker('BTC/USD'))
"
```

### 步骤4: 测试数据格式化
```bash
python -c "
from api.agents.data_formatter import DataFormatter
formatter = DataFormatter()

# 测试真实的Roostoo格式
roostoo_data = {
    'Success': True,
    'Data': {
        'BTC/USD': {
            'LastPrice': 103149.88,
            'Change': 0.0189,
            'UnitTradeValue': 3213826873.11
        }
    }
}
formatted = formatter.format_ticker(roostoo_data, 'BTC/USD')
print('Formatted:', formatted)
print('Price extracted:', formatted.get('price'))
"
```

### 步骤5: 测试完整数据流
```bash
python test_complete_system.py
```

## 清理测试文件

### 自动清理（推荐）
```bash
# 运行清理脚本（会询问是否保留test_complete_system.py）
bash cleanup_test_files.sh
```

### 手动清理
```bash
# 删除所有测试文件（保留test_complete_system.py）
rm -f test_formatter.py test_data_flow.py verify_system.py full_test.sh

# 如果想删除所有测试相关文件
rm -f test_*.py verify_*.py *_test.sh cleanup_test_files.sh
```

## 问题排查命令

### 检查数据格式
```bash
python -c "
from api.roostoo_client import RoostooClient
from api.agents.data_formatter import DataFormatter

client = RoostooClient()
formatter = DataFormatter()

# 获取原始数据
raw = client.get_ticker('BTC/USD')
print('Raw data structure:')
print('  Keys:', list(raw.keys()))
if 'Data' in raw:
    print('  Data keys:', list(raw['Data'].keys()))
    if 'BTC/USD' in raw['Data']:
        print('  BTC/USD keys:', list(raw['Data']['BTC/USD'].keys()))

# 格式化
formatted = formatter.format_ticker(raw, 'BTC/USD')
print('\nFormatted data:')
print('  Price:', formatted.get('price'))
print('  Change:', formatted.get('change_24h'))
"
```

### 检查Agent数据接收
```bash
python -c "
import time
from api.agents.manager import AgentManager
from api.agents.market_collector import MarketDataCollector
from api.agents.prompt_manager import PromptManager

mgr = AgentManager()
pm = PromptManager()
pm.get_system_prompt('TestAgent')
mgr.add_agent('test', pm.get_system_prompt('TestAgent'))
mgr.start()

collector = MarketDataCollector(mgr.bus, mgr.market_topic, ['BTC/USD'], 3.0)
collector.start()

time.sleep(8)
snapshot = collector.get_latest_snapshot()
print('Snapshot:', snapshot)
if snapshot and snapshot.get('ticker'):
    print('Ticker price:', snapshot['ticker'].get('price'))

collector.stop()
mgr.stop()
"
```

## 预期输出示例

### 成功的数据流测试输出
```
============================================================
[测试 6/6] 完整数据流测试
============================================================

[1] 初始化组件...
✓ Components initialized

[2] 创建并启动 Agent...
✓ Agent started

[3] 启动市场数据采集器...
[MarketDataCollector] Started. Collecting data every 3.0s
✓ Data collector started

[4] 等待市场数据采集 (10秒)...
[MarketDataCollector] Published ticker for BTC/USD: $103149.88
[MarketDataCollector] Published balance: $50000.00

[5] 检查采集到的数据...
✓ Market snapshot created
  ✓ Ticker data: Price = $103149.88
  ✓ Balance data: Total = $50000.00

[6] 测试Prompt生成...
✓ Trading prompt generated (1234 chars)
✓ Spot trading prompt generated (5678 chars)

[7] 检查Agent决策...
✓ Received 1 decision(s)
  1. Agent: test_agent
     Decision: Based on current market analysis, BTC/USD is at $103149.88...
```

## 常见问题

### Q: Agent显示没有数据
**A**: 检查DataFormatter是否正确提取了价格：
```bash
python -c "
from api.roostoo_client import RoostooClient
from api.agents.data_formatter import DataFormatter

client = RoostooClient()
formatter = DataFormatter()

raw = client.get_ticker('BTC/USD')
formatted = formatter.format_ticker(raw, 'BTC/USD')
print('Price extracted:', formatted.get('price'))
if formatted.get('price') is None:
    print('ERROR: Price not extracted!')
    print('Raw data:', raw)
"
```

### Q: Prompt格式化错误
**A**: 已修复，使用字符串替换而不是format()。如果仍有问题：
```bash
python -c "
from api.agents.prompt_manager import PromptManager
pm = PromptManager()
prompt = pm.get_spot_trading_prompt(
    date='2025-01-07',
    account_equity='10000',
    available_cash='8000',
    positions='BTC: 0.1'
)
if prompt:
    print('✓ Prompt generated successfully')
else:
    print('✗ Prompt generation failed')
"
```

## 测试文件说明

### 保留的文件
- **`test_complete_system.py`**: 整合了所有测试功能的主测试文件
- **`TESTING_GUIDE.md`**: 详细的测试指南文档
- **`BUG_FIX_REPORT.md`**: Bug修复报告

### 已整合的功能
`test_complete_system.py` 整合了以下功能：
1. ✅ 系统验证（原`verify_system.py`）
2. ✅ LLM连接测试
3. ✅ Roostoo连接测试
4. ✅ 数据格式化测试
5. ✅ Prompt管理器测试
6. ✅ 完整数据流测试（原`test_data_flow.py`）

### 可以删除的文件
运行清理脚本后，以下文件会被删除：
- `test_formatter.py` (临时测试文件)
- `test_data_flow.py` (已整合到test_complete_system.py)
- `verify_system.py` (已整合到test_complete_system.py)
- `full_test.sh` (已整合到test_complete_system.py)

## 一键测试命令

```bash
# 完整测试流程
source .venv/bin/activate && \
python test_complete_system.py --full
```

## 验证修复

修复后，运行测试应该看到：
```bash
python test_complete_system.py
```

**关键检查点**:
1. ✅ `Price extracted: 103149.88` (不再是None)
2. ✅ `Published ticker for BTC/USD: $103149.88` (不再是$N/A)
3. ✅ Agent决策包含实际价格数据
4. ✅ 没有"missing key"错误

