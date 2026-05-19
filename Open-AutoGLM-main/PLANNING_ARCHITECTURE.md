# Phone-Agent 与 Mobile-Agent-E 规划架构差异说明

## 一、为什么 Phone-Agent 没有 prompt_planning？

### 1.1 架构设计差异

**Phone-Agent 的架构：**
- **端到端设计**：模型在一次调用中同时完成思考和动作决策
- **无独立规划阶段**：没有将规划（planning）和执行（action）分离
- **单阶段推理**：每次模型调用 = 思考（thinking）+ 动作（action）

**Mobile-Agent-E 的架构：**
- **多阶段设计**：将任务分解为多个独立的阶段
- **独立规划阶段**：有专门的 Manager 进行高级规划
- **独立执行阶段**：有专门的 Operator 进行动作决策
- **多阶段推理**：每个迭代包含多个独立的 LLM 调用

### 1.2 具体对比

| 维度 | Phone-Agent | Mobile-Agent-E |
|------|-------------|----------------|
| **规划方式** | 模型在 thinking 中隐式规划 | 独立的 Manager 阶段显式规划 |
| **规划记录** | 无独立的 `prompt_planning` | 有 `prompt_planning` 记录 |
| **执行记录** | 有 `prompt_action` 记录 | 有 `prompt_action` 记录 |
| **模型调用** | 每次 1 次调用（思考+动作） | 每次迭代 3-4 次调用（规划+执行+反思+记录） |

## 二、Phone-Agent 的思考过程

### 2.1 模型响应结构

Phone-Agent 的模型响应包含两部分：

1. **Thinking（思考）**：模型分析当前状态，规划下一步行动
2. **Action（动作）**：模型输出具体的动作指令

**示例：**
```
Thinking: "用户想要打开美团并搜索附近的火锅店。我需要：
1. 首先打开美团应用
2. 然后在美团中搜索附近的火锅店

从截图中我可以看到美团应用在屏幕上，位置在第一行第三个，黄色图标。
我可以直接点击它，或者使用Launch功能。

根据指南，我应该使用Launch功能来打开应用，这样更直接。美团在允许的应用列表中。

让我先启动美团应用。"

Action: do(action="Launch", app="美团")
```

### 2.2 日志记录方式

在 `steps.json` 中，Phone-Agent 记录：

```json
{
  "step": 1,
  "operation": "action",
  "prompt_action": "打开美团搜索附近的火锅店\n\n{\"current_app\": \"System Home\"}",
  "action_thought": "用户想要打开美团并搜索附近的火锅店...",
  "action_object": {
    "_metadata": "do",
    "action": "Launch",
    "app": "美团"
  }
}
```

**注意：**
- `prompt_action`：发送给模型的 prompt（包含任务和屏幕信息）
- `action_thought`：模型的思考过程（相当于隐式的规划）
- 没有独立的 `prompt_planning`，因为规划包含在模型的 thinking 中

## 三、Mobile-Agent-E 的规划过程

### 3.1 多阶段处理

Mobile-Agent-E 每个迭代包含：

1. **Manager（规划阶段）**：
   - 输入：任务、当前状态、历史信息
   - 输出：高级计划（plan）、当前子目标（current_subgoal）
   - 记录：`prompt_planning`、`raw_response`（规划响应）

2. **Operator（执行阶段）**：
   - 输入：计划、当前子目标、屏幕截图
   - 输出：具体动作（action）
   - 记录：`prompt_action`、`raw_response`（动作响应）

3. **ActionReflector（反思阶段）**：
   - 输入：动作前后的截图
   - 输出：动作结果（outcome）、错误描述、进度状态

4. **NoteTaker（记录阶段）**：
   - 输入：成功后的截图
   - 输出：重要信息记录

### 3.2 日志记录方式

在 `steps.json` 中，Mobile-Agent-E 记录：

```json
{
  "step": 1,
  "operation": "planning",
  "prompt_planning": "### User Instruction ###\n打开美团搜索附近的火锅店\n\n---\nThink step by step...",
  "raw_response": "### Thought ###\n...\n### Plan ###\n1. 打开美团应用\n2. 搜索火锅店...",
  "plan": "1. 打开美团应用\n2. 搜索火锅店...",
  "current_subgoal": "打开美团应用"
},
{
  "step": 1,
  "operation": "action",
  "prompt_action": "### User Instruction ###\n打开美团搜索附近的火锅店\n\n### Overall Plan ###\n...",
  "raw_response": "### Thought ###\n...\n### Action ###\n{\"name\":\"Open_App\",\"arguments\":{\"app_name\":\"美团\"}}",
  "action_object": {"name": "Open_App", "arguments": {"app_name": "美团"}}
}
```

## 四、为什么 Phone-Agent 这样设计？

### 4.1 设计理念

1. **简化架构**：
   - 减少系统复杂度
   - 降低维护成本
   - 提高执行效率

2. **端到端学习**：
   - 模型可以学习从状态到动作的完整映射
   - 不需要显式规划也能完成任务

3. **减少延迟**：
   - 每次只需要 1 次模型调用
   - 比多阶段设计更快

### 4.2 优缺点

**优点：**
- ✅ 架构简单，易于理解和维护
- ✅ 执行速度快（每次 1 次调用）
- ✅ 资源消耗少（token 使用更少）

**缺点：**
- ❌ 缺乏显式规划，可能走弯路
- ❌ 无法记录规划过程（只有 action_thought）
- ❌ 难以进行高级规划（复杂任务可能效率低）

## 五、如何理解 Phone-Agent 的"规划"？

### 5.1 隐式规划

Phone-Agent 的规划是**隐式的**，包含在模型的 `action_thought` 中：

```json
{
  "action_thought": "用户想要打开美团并搜索附近的火锅店。我需要：
  1. 首先打开美团应用
  2. 然后在美团中搜索附近的火锅店
  
  从截图中我可以看到美团应用在屏幕上...
  
  让我先启动美团应用。"
}
```

这个 `action_thought` 实际上包含了：
- **任务理解**：理解用户意图
- **状态分析**：分析当前屏幕状态
- **规划**：制定行动计划（步骤 1、2）
- **决策**：选择具体动作（Launch）

### 5.2 与 Mobile-Agent-E 的对应关系

| Mobile-Agent-E | Phone-Agent |
|----------------|-------------|
| `prompt_planning` + `raw_response`（规划） | `action_thought`（隐式规划） |
| `prompt_action` + `raw_response`（执行） | `prompt_action` + `raw_response`（执行） |

## 六、如果需要显式规划记录

如果您需要像 Mobile-Agent-E 一样记录显式的规划过程，可以考虑：

### 6.1 方案 1：修改日志记录（推荐）

在记录日志时，将 `action_thought` 中的规划部分提取出来：

```python
# 在 agent.py 的日志记录部分
step_log = {
    "step": self._step_count,
    "operation": "action",
    "prompt_action": prompt_action,
    "action_thought": response.thinking,  # 包含隐式规划
    "implicit_planning": response.thinking,  # 可以添加这个字段
    # ...
}
```

### 6.2 方案 2：添加规划阶段（架构改动）

如果确实需要独立的规划阶段，需要：
1. 添加 Manager 组件（类似 Mobile-Agent-E）
2. 在每次迭代开始时进行规划
3. 记录 `prompt_planning` 和规划结果

但这会改变 Phone-Agent 的架构设计，需要较大的改动。

## 七、总结

1. **Phone-Agent 没有 `prompt_planning` 是设计选择**，不是 bug
2. **规划是隐式的**，包含在模型的 `action_thought` 中
3. **架构更简单**，但可能缺乏显式规划的优势
4. **如果需要显式规划**，可以：
   - 方案 1：在日志中添加 `implicit_planning` 字段记录 `action_thought`
   - 方案 2：添加独立的规划阶段（需要架构改动）

**当前建议：**
- 如果只是需要记录规划信息，可以添加 `implicit_planning` 字段
- 如果需要真正的多阶段规划，建议参考 Mobile-Agent-E 的架构




