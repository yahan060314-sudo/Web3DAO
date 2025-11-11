# AI 决策管理使用指南

## 📋 概述

本文档介绍如何使用新的决策管理系统，包括决策存储、验证、多AI综合等功能。

## 🎯 核心功能

### 1. 决策存储
- 所有决策自动存储到 SQLite 数据库
- 记录决策的完整信息（agent、decision、market_snapshot、timestamp等）
- 支持查询和分析历史决策

### 2. 决策验证
- 价格合理性验证（检查价格是否在合理范围内）
- 数量合理性验证（检查数量是否在合理范围内）
- 时间有效性验证（检查决策是否过期）
- 余额充足性验证（检查账户余额是否充足）

### 3. 多AI决策综合
- 支持多个AI的决策综合（投票机制）
- 时间窗口内的决策自动综合
- 共识决策优先执行

### 4. 执行结果记录
- 记录所有执行结果（成功/失败）
- 记录执行时间
- 记录错误信息

## 🚀 快速开始

### 方式1: 使用增强版执行器（推荐）

```python
from api.agents.bus import MessageBus
from api.agents.enhanced_executor import EnhancedTradeExecutor

# 1. 创建消息总线
bus = MessageBus()

# 2. 创建增强版执行器
executor = EnhancedTradeExecutor(
    bus=bus,
    decision_topic="decisions",
    default_pair="BTC/USD",
    dry_run=True,  # 测试模式，不真正下单
    enable_decision_manager=True,  # 启用决策管理器
    db_path="decisions.db",  # 数据库文件路径
    enable_multi_ai_consensus=True  # 启用多AI决策综合
)

# 3. 启动执行器
executor.start()

# 4. 使用现有的 Agent 系统
# Agent 的决策会自动存储和验证
```

### 方式2: 直接使用决策管理器

```python
from api.agents.decision_manager import DecisionManager

# 1. 创建决策管理器
manager = DecisionManager(
    db_path="decisions.db",
    decision_timeout=5.0,  # 决策有效期（秒）
    enable_multi_ai_consensus=True
)

# 2. 添加决策
decision_msg = {
    "agent": "agent1",
    "decision": '{"action": "buy", "quantity": 0.01, "symbol": "BTCUSDT"}',
    "market_snapshot": {
        "ticker": {"price": 50000.0},
        "balance": {}
    },
    "timestamp": time.time(),
    "json_valid": True
}

decision_id = manager.add_decision(decision_msg)

# 3. 验证决策
parsed_decision = {
    "side": "BUY",
    "quantity": 0.01,
    "price": None,
    "pair": "BTC/USD"
}

is_valid, error_msg = manager.validate_decision(
    parsed_decision,
    current_price=50000.0
)

if is_valid:
    # 执行交易
    # ...
    # 记录执行结果
    manager.record_execution_result(
        decision_id=decision_id,
        order_id="order_123",
        status="success",
        execution_time=0.5
    )

# 4. 获取统计信息
stats = manager.get_statistics(hours=24)
print(f"总决策数: {stats['total_decisions']}")
print(f"成功率: {stats['success_rate']:.2%}")
```

## 📊 数据库结构

### decisions 表
- `id`: 决策ID（主键）
- `agent`: Agent名称
- `decision`: 决策文本
- `decision_json`: 决策JSON（如果可用）
- `market_snapshot`: 市场快照（JSON格式）
- `timestamp`: 时间戳
- `json_valid`: JSON格式是否有效
- `status`: 状态（pending/success/failed/skipped）
- `created_at`: 创建时间

### execution_results 表
- `id`: 执行结果ID（主键）
- `decision_id`: 决策ID（外键）
- `order_id`: 订单ID
- `status`: 执行状态（success/failed/skipped）
- `error`: 错误信息
- `execution_time`: 执行时间（秒）
- `executed_at`: 执行时间

### market_data 表
- `id`: 市场数据ID（主键）
- `timestamp`: 时间戳
- `ticker`: Ticker数据（JSON格式）
- `balance`: 余额数据（JSON格式）
- `created_at`: 创建时间

## 🔍 查询和分析

### 查询决策

```python
# 获取决策
decision = manager.get_decision(decision_id)
print(f"Agent: {decision['agent']}")
print(f"Decision: {decision['decision']}")
print(f"Status: {decision['status']}")
```

### 获取统计信息

```python
# 获取24小时内的统计信息
stats = manager.get_statistics(hours=24)
print(f"总决策数: {stats['total_decisions']}")
print(f"成功执行数: {stats['success_count']}")
print(f"失败执行数: {stats['fail_count']}")
print(f"成功率: {stats['success_rate']:.2%}")
print(f"平均执行时间: {stats['avg_execution_time']:.3f}秒")
```

### 使用 SQL 查询

```python
import sqlite3

conn = sqlite3.connect("decisions.db")
cursor = conn.cursor()

# 查询所有成功的决策
cursor.execute("""
    SELECT * FROM decisions 
    WHERE status = 'success' 
    ORDER BY timestamp DESC 
    LIMIT 10
""")

for row in cursor.fetchall():
    print(row)

conn.close()
```

## 🔧 配置选项

### EnhancedTradeExecutor 配置

```python
executor = EnhancedTradeExecutor(
    bus=bus,  # 消息总线
    decision_topic="decisions",  # 决策topic名称
    default_pair="BTC/USD",  # 默认交易对
    dry_run=False,  # 是否测试模式
    enable_decision_manager=True,  # 是否启用决策管理器
    db_path="decisions.db",  # 数据库文件路径
    enable_multi_ai_consensus=True  # 是否启用多AI决策综合
)
```

### DecisionManager 配置

```python
manager = DecisionManager(
    db_path="decisions.db",  # 数据库文件路径
    decision_timeout=5.0,  # 决策有效期（秒）
    enable_multi_ai_consensus=True  # 是否启用多AI决策综合
)
```

## 🎨 多AI决策综合

### 工作原理

1. **收集决策**: 在时间窗口内收集多个AI的决策
2. **解析决策**: 解析每个决策的side、quantity、price等
3. **投票机制**: 统计buy和sell的数量
4. **共识决策**: 如果多数AI同意，生成共识决策
5. **执行共识**: 执行共识决策（使用平均数量）

### 示例

```python
# 假设有3个AI的决策
decisions = [
    {"side": "BUY", "quantity": 0.01, "pair": "BTC/USD"},
    {"side": "BUY", "quantity": 0.02, "pair": "BTC/USD"},
    {"side": "SELL", "quantity": 0.01, "pair": "BTC/USD"}
]

# 获取共识决策
consensus = manager.get_consensus_decision(decisions)
# 返回: {"side": "BUY", "quantity": 0.015, "pair": "BTC/USD", "consensus_count": 2, "total_decisions": 3}
```

## 📈 性能优化

### 1. 数据库优化
- 使用索引加速查询
- 定期清理旧数据
- 使用连接池

### 2. 决策验证优化
- 缓存市场数据
- 批量验证决策
- 异步验证

### 3. 多AI综合优化
- 调整时间窗口
- 优化投票算法
- 缓存共识结果

## 🐛 故障排查

### 问题1: 数据库文件不存在
**解决**: 决策管理器会自动创建数据库文件

### 问题2: 决策验证失败
**解决**: 检查决策格式、价格范围、数量范围等

### 问题3: 多AI综合不工作
**解决**: 检查时间窗口设置、决策格式等

### 问题4: 执行结果未记录
**解决**: 检查决策管理器是否启用、数据库连接是否正常

## 📚 相关文档

- [AI_DECISION_TO_MARKET_ANALYSIS.md](./AI_DECISION_TO_MARKET_ANALYSIS.md) - 详细的分析文档
- [api/agents/decision_manager.py](./api/agents/decision_manager.py) - 决策管理器实现
- [api/agents/enhanced_executor.py](./api/agents/enhanced_executor.py) - 增强版执行器实现
- [api/agents/enhanced_example.py](./api/agents/enhanced_example.py) - 使用示例

## 🎯 最佳实践

1. **启用决策管理器**: 在生产环境中始终启用决策管理器
2. **启用多AI综合**: 如果有多个AI，启用多AI决策综合
3. **定期备份数据库**: 定期备份决策数据库
4. **监控统计信息**: 定期查看统计信息，优化决策质量
5. **验证决策**: 始终验证决策的有效性
6. **记录执行结果**: 记录所有执行结果，便于分析和优化

## 🔄 迁移指南

### 从普通执行器迁移到增强版执行器

```python
# 旧代码
from api.agents.executor import TradeExecutor

executor = TradeExecutor(bus, "decisions", "BTC/USD", dry_run=False)
executor.start()

# 新代码
from api.agents.enhanced_executor import EnhancedTradeExecutor

executor = EnhancedTradeExecutor(
    bus=bus,
    decision_topic="decisions",
    default_pair="BTC/USD",
    dry_run=False,
    enable_decision_manager=True,
    enable_multi_ai_consensus=True
)
executor.start()
```

## 📞 支持

如有问题，请查看：
1. [AI_DECISION_TO_MARKET_ANALYSIS.md](./AI_DECISION_TO_MARKET_ANALYSIS.md) - 详细分析
2. [api/agents/enhanced_example.py](./api/agents/enhanced_example.py) - 使用示例
3. 代码注释和文档字符串

