# Token 使用说明：prompt_tokens 与 completion_tokens 的区别

## 一、核心概念

### 1.1 Token 类型定义

- **prompt_tokens（输入 token）**：发送给模型的输入内容
  - System prompt
  - User messages（包括任务描述、屏幕信息等）
  - 历史对话上下文

- **completion_tokens（输出 token）**：模型生成的内容
  - Thinking（思考过程）
  - Action（动作指令）

### 1.2 重要区别

**`action_thought` 是输出，不是输入！**

- `action_thought` = 模型生成的思考内容
- 属于 `completion_tokens`，不属于 `prompt_tokens`

## 二、Mobile-Agent-E 的 Token 记录

### 2.1 架构特点

Mobile-Agent-E 有**多个独立的 API 调用**：

1. **Manager（规划阶段）**：
   - 输入：`prompt_planning` → **prompt_tokens（规划）**
   - 输出：规划结果 → **completion_tokens（规划）**

2. **Operator（执行阶段）**：
   - 输入：`prompt_action` → **prompt_tokens（执行）**
   - 输出：动作结果 → **completion_tokens（执行）**

### 2.2 Token 计算

**每个阶段的 token 使用：**
- Planning 阶段：`prompt_tokens（规划）` + `completion_tokens（规划）`
- Action 阶段：`prompt_tokens（执行）` + `completion_tokens（执行）`

**总 token 使用：**
- 总 prompt_tokens = prompt_tokens（规划） + prompt_tokens（执行）
- 总 completion_tokens = completion_tokens（规划） + completion_tokens（执行）

## 三、Phone-Agent 的 Token 记录

### 3.1 架构特点

Phone-Agent 是**单次 API 调用**：

- 输入：`prompt_action`（包含 system prompt + 任务 + 屏幕信息）
- 输出：`action_thought`（思考） + `action`（动作）

### 3.2 Token 计算

**单次调用的 token 使用：**
- `prompt_tokens` = 所有输入内容（system prompt + prompt_action）
- `completion_tokens` = 所有输出内容（action_thought + action）

**注意：**
- `action_thought` 是模型**输出**的一部分
- 属于 `completion_tokens`，**不是** `prompt_tokens`

## 四、为什么不能将 action_thought 算入 prompt_tokens？

### 4.1 技术原因

```
┌─────────────────────────────────────┐
│         API 调用流程                │
├─────────────────────────────────────┤
│ 输入（prompt_tokens）：              │
│   - System prompt                   │
│   - User message (prompt_action)    │
│   - 历史上下文                       │
├─────────────────────────────────────┤
│ 输出（completion_tokens）：          │
│   - action_thought (思考)          │
│   - action (动作)                   │
└─────────────────────────────────────┘
```

**`action_thought` 是模型生成的，不是我们输入的！**

### 4.2 类比说明

就像问问题：
- **prompt_tokens** = 您说的话（问题）
- **completion_tokens** = AI 的回答（包括思考过程和答案）

您不能把 AI 的回答算作您说的话！

## 五、正确的 Token 记录方式

### 5.1 Phone-Agent 当前记录

```json
{
  "step": 1,
  "operation": "action",
  "prompt_action": "打开美团搜索附近的火锅店\n\n{\"current_app\": \"System Home\"}",
  "action_thought": "用户想要打开美团并搜索附近的火锅店...",
  "prompt_tokens": 3239,        // ✅ 正确：输入 token
  "completion_tokens": 108,      // ✅ 正确：输出 token（包括 thinking + action）
  "total_tokens": 3347,
  "prompt_action_tokens": 3239   // ✅ 正确：action 阶段的 prompt tokens
}
```

### 5.2 Mobile-Agent-E 的记录方式

```json
{
  "step": 1,
  "operation": "planning",
  "prompt_planning": "...",
  "raw_response": "...",
  // 注意：Mobile-Agent-E 的 steps.json 中通常不直接记录 token
  // token 使用可能记录在单独的 usage_tracking.jsonl 文件中
},
{
  "step": 1,
  "operation": "action",
  "prompt_action": "...",
  "raw_response": "..."
}
```

## 六、如果需要更详细的 Token 记录

### 6.1 方案 1：记录完整的 Token 信息（当前已实现）

Phone-Agent 已经记录了：
- `prompt_tokens`：所有输入 token
- `completion_tokens`：所有输出 token（包括 thinking + action）
- `total_tokens`：总 token 数

### 6.2 方案 2：估算 thinking 和 action 的 token 分配

如果需要区分 thinking 和 action 的 token 使用，可以估算：

```python
# 在 agent.py 中
if response.completion_tokens is not None:
    # 估算：thinking 和 action 的 token 分配
    thinking_text = response.thinking
    action_text = response.action
    
    # 简单估算（实际可能需要更精确的 tokenizer）
    thinking_tokens_estimate = len(thinking_text.split()) * 1.3  # 粗略估算
    action_tokens_estimate = len(action_text.split()) * 1.3
    
    step_log["completion_tokens_thinking"] = int(thinking_tokens_estimate)
    step_log["completion_tokens_action"] = int(action_tokens_estimate)
```

### 6.3 方案 3：使用 tokenizer 精确计算

如果需要精确计算，可以使用 tokenizer：

```python
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("model_name")

thinking_tokens = len(tokenizer.encode(response.thinking))
action_tokens = len(tokenizer.encode(response.action))
```

## 七、总结

### 7.1 关键点

1. **`action_thought` 是输出，不是输入**
   - 属于 `completion_tokens`
   - 不属于 `prompt_tokens`

2. **Phone-Agent 的 prompt_tokens 已经包含了所有输入**
   - System prompt
   - prompt_action（任务 + 屏幕信息）
   - 历史上下文

3. **Mobile-Agent-E 的 prompt_tokens 是分开的**
   - prompt_planning 的 token（规划阶段）
   - prompt_action 的 token（执行阶段）

### 7.2 对应关系

| Mobile-Agent-E | Phone-Agent |
|----------------|-------------|
| `prompt_planning` → prompt_tokens（规划） | 无独立规划阶段 |
| `prompt_action` → prompt_tokens（执行） | `prompt_action` → prompt_tokens |
| 规划输出 → completion_tokens（规划） | `action_thought` → completion_tokens（部分） |
| 动作输出 → completion_tokens（执行） | `action` → completion_tokens（部分） |

### 7.3 回答您的问题

**问题：** Phone-Agent 的 prompt_tokens 可以算上 action_thought 和 prompt_action 吗？

**答案：** **不能**。

- ✅ `prompt_action` 可以算入 `prompt_tokens`（已经是了）
- ❌ `action_thought` **不能**算入 `prompt_tokens`（它是输出，属于 `completion_tokens`）

**正确的理解：**
- `prompt_tokens` = 所有输入（包括 prompt_action）
- `completion_tokens` = 所有输出（包括 action_thought + action）

**如果需要记录 thinking 的 token：**
- 应该记录为 `completion_tokens_thinking`（输出 token 的一部分）
- 而不是 `prompt_tokens`




