# Prompt传入流程详细说明

## 概述

**回答**：**部分统一处理** - 系统prompt每个Agent可以不同，用户prompt统一广播给所有Agent。

## 涉及的文件

1. **`api/agents/prompt_manager.py`** - Prompt管理器，负责创建和格式化prompt
2. **`api/agents/manager.py`** - Agent管理器，负责创建Agent和广播prompt
3. **`api/agents/base_agent.py`** - Agent基类，负责接收和处理prompt
4. **`api/agents/bus.py`** - 消息总线，负责prompt的传递

## 两种Prompt类型

### 1. 系统Prompt（System Prompt）- 每个Agent可以不同

**作用**：定义Agent的角色、行为规则和输出格式

**传入时机**：在创建Agent时传入

**流程**：

```
用户代码
  ↓
AgentManager.add_agent(name, system_prompt)
  ↓
BaseAgent.__init__(system_prompt=system_prompt)
  ↓
BaseAgent.system_prompt = system_prompt  # 存储为实例变量
```

**代码位置**：

```python
# manager.py 第26行
def add_agent(self, name: str, system_prompt: str) -> None:
    agent = BaseAgent(
        name=name,
        bus=self.bus,
        market_topic=self.market_topic,
        dialog_topic=self.dialog_topic,
        decision_topic=self.decision_topic,
        system_prompt=system_prompt,  # ← 每个Agent可以不同
    )
    self.agents.append(agent)
```

**特点**：
- ✅ 每个Agent可以有自己独特的system_prompt
- ✅ 在Agent创建时确定，之后不会改变
- ✅ 存储在Agent实例中（`self.system_prompt`）

**使用示例**：

```python
pm = PromptManager()

# Agent 1: 保守策略
system_prompt_1 = pm.get_system_prompt(
    agent_name="ConservativeAgent",
    risk_level="conservative"
)

# Agent 2: 激进策略
system_prompt_2 = pm.get_system_prompt(
    agent_name="AggressiveAgent",
    risk_level="aggressive"
)

mgr = AgentManager()
mgr.add_agent("agent1", system_prompt_1)  # 使用保守prompt
mgr.add_agent("agent2", system_prompt_2)  # 使用激进prompt
```

### 2. 用户Prompt（User Prompt）- 统一广播给所有Agent

**作用**：给Agent的具体任务指令（如"分析市场并做出决策"）

**传入时机**：运行时通过广播传入

**流程**：

```
用户代码 / PromptManager
  ↓
AgentManager.broadcast_prompt(role, content)
  ↓
MessageBus.publish("dialog_prompts", {"role": role, "content": content})
  ↓
所有订阅了"dialog_prompts"的Agent同时接收
  ↓
BaseAgent._handle_dialog(msg)
  ↓
BaseAgent.dialog_history.append(msg)  # 添加到对话历史
  ↓
BaseAgent._make_decision_from_dialog(msg)
  ↓
BaseAgent._generate_decision(content)  # 使用system_prompt + 这个user_prompt生成决策
```

**代码位置**：

```python
# manager.py 第51行
def broadcast_prompt(self, role: str, content: str) -> None:
    self.bus.publish(self.dialog_topic, {"role": role, "content": content})
    # ↑ 发布到"dialog_prompts" topic，所有订阅的Agent都会收到
```

```python
# base_agent.py 第36行
self.dialog_sub: Subscription = bus.subscribe(dialog_topic)  # 订阅"dialog_prompts"

# base_agent.py 第67-69行
dialog_msg = self.dialog_sub.recv(timeout=0.01)
if dialog_msg is not None:
    self._handle_dialog(dialog_msg)  # 所有Agent都会处理
```

**特点**：
- ✅ 统一广播：一次调用，所有Agent同时接收
- ✅ 实时传入：可以在运行时随时广播
- ✅ 添加到对话历史：每个Agent维护自己的对话历史

**使用示例**：

```python
pm = PromptManager()
mgr = AgentManager()

# 创建Agent
mgr.add_agent("agent1", system_prompt_1)
mgr.add_agent("agent2", system_prompt_2)
mgr.start()

# 统一广播prompt给所有Agent
spot_prompt = pm.create_spot_prompt_from_market_data(market_snapshot)
mgr.broadcast_prompt(role="user", content=spot_prompt)
# ↑ 所有Agent（agent1和agent2）都会同时收到这个prompt
```

## 完整流程示例

### 场景：创建3个Agent，然后统一发送交易指令

```python
from api.agents.manager import AgentManager
from api.agents.prompt_manager import PromptManager

# 1. 创建PromptManager
pm = PromptManager()

# 2. 为每个Agent创建不同的系统prompt
system_prompt_1 = pm.get_system_prompt(
    agent_name="Agent1",
    risk_level="conservative"
)

system_prompt_2 = pm.get_system_prompt(
    agent_name="Agent2",
    risk_level="moderate"
)

system_prompt_3 = pm.get_system_prompt(
    agent_name="Agent3",
    risk_level="aggressive"
)

# 3. 创建AgentManager并添加Agent
mgr = AgentManager()
mgr.add_agent("agent1", system_prompt_1)  # 每个Agent有不同的system_prompt
mgr.add_agent("agent2", system_prompt_2)
mgr.add_agent("agent3", system_prompt_3)
mgr.start()

# 4. 统一广播用户prompt给所有Agent
market_snapshot = {...}  # 市场数据
spot_prompt = pm.create_spot_prompt_from_market_data(market_snapshot)
mgr.broadcast_prompt(role="user", content=spot_prompt)
# ↑ 所有3个Agent都会同时收到这个prompt
```

## 数据流图

```
┌─────────────────────────────────────────────────────────┐
│  PromptManager (创建prompt)                            │
└─────────────────────────────────────────────────────────┘
                    │
                    ├─→ get_system_prompt() → 系统prompt（每个Agent不同）
                    │
                    └─→ create_spot_prompt_from_market_data() → 用户prompt（统一）
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  AgentManager                                           │
│  - add_agent(name, system_prompt)  ← 每个Agent不同    │
│  - broadcast_prompt(role, content)  ← 统一广播         │
└─────────────────────────────────────────────────────────┘
                            │
                            ├─→ MessageBus.publish("dialog_prompts", ...)
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  MessageBus (消息总线)                                  │
│  Topic: "dialog_prompts"                                │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  BaseAgent1  │  │  BaseAgent2  │  │  BaseAgent3  │
│              │  │              │  │              │
│ system_prompt│  │ system_prompt│  │ system_prompt│
│ (保守)       │  │ (中等)       │  │ (激进)       │
│              │  │              │  │              │
│ dialog_sub   │  │ dialog_sub   │  │ dialog_sub   │
│ (订阅)       │  │ (订阅)       │  │ (订阅)       │
└──────────────┘  └──────────────┘  └──────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                   所有Agent同时接收
                   用户prompt（统一）
```

## 关键点总结

### 系统Prompt（每个Agent不同）

1. **传入方式**：`AgentManager.add_agent(name, system_prompt)`
2. **存储位置**：`BaseAgent.system_prompt`（实例变量）
3. **特点**：每个Agent可以有不同的system_prompt
4. **使用时机**：每次调用LLM时都会使用（`_generate_decision()`方法）

### 用户Prompt（统一广播）

1. **传入方式**：`AgentManager.broadcast_prompt(role, content)`
2. **传递机制**：通过MessageBus的"dialog_prompts" topic
3. **特点**：一次广播，所有Agent同时接收
4. **存储位置**：`BaseAgent.dialog_history`（每个Agent维护自己的历史）
5. **使用时机**：立即触发决策生成（`_handle_dialog()` → `_generate_decision()`）

## 代码交互细节

### 文件1: `prompt_manager.py`

**职责**：
- 创建系统prompt：`get_system_prompt()`
- 创建用户prompt：`create_trading_prompt()`, `create_spot_prompt_from_market_data()`

**不直接与Agent交互**，只负责生成prompt字符串

### 文件2: `manager.py`

**职责**：
- 创建Agent时传入系统prompt：`add_agent(name, system_prompt)`
- 广播用户prompt：`broadcast_prompt(role, content)`

**关键方法**：
```python
def add_agent(self, name: str, system_prompt: str) -> None:
    # 创建Agent，传入系统prompt（每个Agent可以不同）
    
def broadcast_prompt(self, role: str, content: str) -> None:
    # 统一广播用户prompt给所有Agent
    self.bus.publish(self.dialog_topic, {"role": role, "content": content})
```

### 文件3: `base_agent.py`

**职责**：
- 接收系统prompt：在`__init__`时存储
- 接收用户prompt：通过订阅"dialog_prompts" topic
- 处理prompt：`_handle_dialog()` → `_generate_decision()`

**关键方法**：
```python
def __init__(self, ..., system_prompt: str):
    self.system_prompt = system_prompt  # 存储系统prompt
    
def _handle_dialog(self, msg: Dict[str, Any]):
    # 接收用户prompt，添加到历史，立即生成决策
    
def _generate_decision(self, user_prompt: str):
    # 使用system_prompt + user_prompt + 市场数据生成决策
    messages = [
        {"role": "system", "content": self.system_prompt},  # 系统prompt
        {"role": "system", "content": market_data},         # 市场数据
        {"role": "user", "content": user_prompt}            # 用户prompt
    ]
```

### 文件4: `bus.py`

**职责**：
- 提供发布/订阅机制
- 传递prompt消息

**关键方法**：
```python
def publish(self, topic: str, message: Any):
    # 发布消息到指定topic
    
def subscribe(self, topic: str) -> Subscription:
    # 订阅topic，返回订阅对象
```

## 总结

✅ **系统Prompt**：每个Agent可以不同，在创建时传入，存储在Agent实例中

✅ **用户Prompt**：统一广播给所有Agent，通过MessageBus的"dialog_prompts" topic传递

✅ **处理流程**：PromptManager创建 → AgentManager管理 → MessageBus传递 → BaseAgent处理

✅ **统一性**：用户prompt是统一处理的（一次广播，所有Agent接收），但每个Agent使用自己的system_prompt和对话历史

