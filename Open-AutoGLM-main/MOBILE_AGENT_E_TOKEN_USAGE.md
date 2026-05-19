# Mobile-Agent-E Token 使用说明

## 概述

Mobile-Agent-E 采用**多阶段架构**，每个阶段都有独立的 LLM 调用，因此每个阶段都有独立的 token 使用记录。

## 各阶段的 Token 分类

### 1. Planning（规划阶段）

**输入（prompt_tokens）包括：**
- System prompt（系统提示）
- `prompt_planning`（规划阶段的完整提示）：
  - 用户指令（User Instruction）
  - 可用快捷方式（Available Shortcuts）
  - 屏幕截图（Screenshot）
  - 历史上下文（如果有）

**输出（completion_tokens）包括：**
- `thought`（思考过程）
- `plan`（整体计划）
- `current_subgoal`（当前子目标）

**代码位置：**
```753:774:Mobile-Agent-E/inference_agent_E.py
        planning_start_time = time.time()
        prompt_planning = manager.get_prompt(info_pool)
        chat_planning = manager.init_chat()
        chat_planning = add_response("user", prompt_planning, chat_planning, image=screenshot_file)
        output_planning = get_reasoning_model_api_response(chat_planning, temperature=temperature)
        parsed_result_planning = manager.parse_response(output_planning)
        
        info_pool.plan = parsed_result_planning['plan']
        info_pool.current_subgoal = parsed_result_planning['current_subgoal']

        ## log ##
        planning_end_time = time.time()
        steps.append({
            "step": iter,
            "operation": "planning",
            "prompt_planning": prompt_planning,
            "error_flag_plan": info_pool.error_flag_plan,
            "raw_response": output_planning,
            "thought": parsed_result_planning['thought'],
            "plan": parsed_result_planning['plan'],
            "current_subgoal": parsed_result_planning['current_subgoal'],
            "duration": planning_end_time - planning_start_time,
        })
```

---

### 2. Action（动作决策阶段）

**输入（prompt_tokens）包括：**
- System prompt（系统提示）
- `prompt_action`（动作阶段的完整提示）：
  - 用户指令（User Instruction）
  - 整体计划（Overall Plan）
  - 进度状态（Progress Status）
  - 当前子目标（Current Subgoal）
  - 屏幕信息（Screen Information）：包括 OCR 文本、图标描述、坐标等
  - 键盘状态（Keyboard status）
  - 提示信息（Tips）
  - 重要笔记（Important Notes）
  - 原子动作列表（Atomic Actions）
  - 快捷方式列表（Shortcuts）
  - 最新动作历史（Latest Action History）
  - 屏幕截图（Screenshot）

**输出（completion_tokens）包括：**
- `action_thought`（动作思考过程）
- `action_object`（动作对象，JSON 格式）
- `action_description`（动作描述）

**代码位置：**
```857:924:Mobile-Agent-E/inference_agent_E.py
        ### Executor: Action Decision ###
        print("\n### Operator ... ###\n")
        action_decision_start_time = time.time()
        prompt_action = operator.get_prompt(info_pool)
        chat_action = operator.init_chat()
        chat_action = add_response("user", prompt_action, chat_action, image=screenshot_file)
        output_action = get_reasoning_model_api_response(chat_action, temperature=temperature)
        parsed_result_action = operator.parse_response(output_action)
        action_thought, action_object_str, action_description = parsed_result_action['thought'], parsed_result_action['action'], parsed_result_action['description']
        action_decision_end_time = time.time()

        info_pool.last_action_thought = action_thought
        ## execute the action ##
        action_execution_start_time = time.time()
        action_object, num_atomic_actions_executed, shortcut_error_message = operator.execute(action_object_str, info_pool, 
                        screenshot_file=screenshot_file, 
                        ocr_detection=perceptor.ocr_detection,
                        ocr_recognition=perceptor.ocr_recognition,
                        thought = action_thought,
                        screenshot_log_dir = os.path.join(log_dir, "screenshots"),
                        iter = str(iter)
                        )
        action_execution_end_time = time.time()
        if action_object is None:
            task_end_time = time.time()
            steps.append({
                "step": iter,
                "operation": "finish",
                "finish_flag": "abnormal",
                "final_info_pool": asdict(info_pool),
                "task_duration": task_end_time - task_start_time,
            })
            with open(log_json_path, "w") as f:
                json.dump(steps, f, indent=4)
            finish(
                info_pool, 
                persistent_tips_path = persistent_tips_path,
                persistent_shortcuts_path = persistent_shortcuts_path
            ) # 
            print("WARNING!!: Abnormal finishing:", action_object_str)
            save_state(log_dir, info_pool, iter, instruction, task_id, steps)
            if screenrecord:
                end_recording(ADB_PATH, output_recording_path=cur_output_recording_path)
            return

        info_pool.last_action = action_object
        info_pool.last_summary = action_description
        
        
        ## log ##
        steps.append({
            "step": iter,
            "operation": "action",
            "prompt_action": prompt_action,
            "raw_response": output_action,
            "action_object": action_object,
            "action_object_str": action_object_str,
            "action_thought": action_thought,
            "action_description": action_description,
            "duration": action_decision_end_time - action_decision_start_time,
            "execution_duration": action_execution_end_time - action_execution_start_time,
        })
```

---

### 3. Action Reflection（动作反思阶段）

**输入（prompt_tokens）包括：**
- System prompt（系统提示）
- `prompt_action_reflect`（反思阶段的完整提示）：
  - 用户指令（User Instruction）
  - 进度状态（Progress Status）
  - 当前子目标（Current Subgoal）
  - 动作前后的两张屏幕截图（Before & After Screenshots）
  - 屏幕信息（Screen Information）

**输出（completion_tokens）包括：**
- `outcome`（结果：A/B/C）
- `error_description`（错误描述）
- `progress_status`（进度状态）

**代码位置：**
```969:1035:Mobile-Agent-E/inference_agent_E.py
        print("\n### Action Reflector ... ###\n")
        ### Action Reflection: Check whether the action works as expected ###
        action_reflection_start_time = time.time()
        prompt_action_reflect = action_reflector.get_prompt(info_pool)
        chat_action_reflect = action_reflector.init_chat()
        chat_action_reflect = add_response_two_image("user", prompt_action_reflect, chat_action_reflect, [last_screenshot_file, screenshot_file])
        output_action_reflect = get_reasoning_model_api_response(chat_action_reflect, temperature=temperature)
        parsed_result_action_reflect = action_reflector.parse_response(output_action_reflect)
        outcome, error_description, progress_status = (
            parsed_result_action_reflect['outcome'], 
            parsed_result_action_reflect['error_description'], 
            parsed_result_action_reflect['progress_status']
        )
        info_pool.progress_status_history.append(progress_status)
        action_reflection_end_time = time.time()

        if "A" in outcome: # Successful. The result of the last action meets the expectation.
            action_outcome = "A"
        elif "B" in outcome: # Failed. The last action results in a wrong page. I need to return to the previous state.
            action_outcome = "B"

            # NOTE: removing the automatic backing; always stopping at the failed state and then there will be a new perception step
            # no automatic backing
            # check how many backs to take
            action_name = action_object['name']
            if action_name in ATOMIC_ACTION_SIGNITURES:
                # back(ADB_PATH) # back one step for atomic actions
                pass
            elif action_name in info_pool.shortcuts:
                # shortcut_object = info_pool.shortcuts[action_name]
                # num_of_atomic_actions = len(shortcut_object['atomic_action_sequence'])
                if shortcut_error_message is not None:
                    error_description += f"; Error occured while executing the shortcut: {shortcut_error_message}"
                # for _ in range(num_atomic_actions_executed):
                #     back(ADB_PATH)   
            else:
                raise ValueError("Invalid action name:", action_name)

        elif "C" in outcome: # Failed. The last action produces no changes.
            action_outcome = "C"
        else:
            raise ValueError("Invalid outcome:", outcome)
        
        # update action history
        info_pool.action_history.append(action_object)
        info_pool.summary_history.append(action_description)
        info_pool.action_outcomes.append(action_outcome)
        info_pool.error_descriptions.append(error_description)
        info_pool.progress_status = progress_status

        ## log ##
        steps.append({
            "step": iter,
            "operation": "action_reflection",
            "prompt_action_reflect": prompt_action_reflect,
            "raw_response": output_action_reflect,
            "outcome": outcome,
            "error_description": error_description,
            "progress_status": progress_status,
            "duration": action_reflection_end_time - action_reflection_start_time,
        })
```

---

### 4. Notetaking（记录重要内容阶段）

**输入（prompt_tokens）包括：**
- System prompt（系统提示）
- `prompt_note`（记录阶段的完整提示）：
  - 用户指令（User Instruction）
  - 当前屏幕截图（Screenshot）
  - 屏幕信息（Screen Information）
  - 历史上下文

**输出（completion_tokens）包括：**
- `important_notes`（重要笔记）

**代码位置：**
```1039:1064:Mobile-Agent-E/inference_agent_E.py
        ### NoteTaker: Record Important Content ###
        if action_outcome == "A":
            print("\n### NoteKeeper ... ###\n")
            # if previous action is successful, record the important content
            notetaking_start_time = time.time()
            prompt_note = notetaker.get_prompt(info_pool)
            chat_note = notetaker.init_chat()
            chat_note = add_response("user", prompt_note, chat_note, image=screenshot_file) # new screenshot
            output_note = get_reasoning_model_api_response(chat_note, temperature=temperature)
            parsed_result_note = notetaker.parse_response(output_note)
            important_notes = parsed_result_note['important_notes']
            info_pool.important_notes = important_notes
            os.remove(last_screenshot_file)
            
            notetaking_end_time = time.time()
            steps.append({
                "step": iter,
                "operation": "notetaking",
                "prompt_note": prompt_note,
                "raw_response": output_note,
                "important_notes": important_notes,
                "duration": notetaking_end_time - notetaking_start_time,
            })
            print("Important Notes:", important_notes)
            with open(log_json_path, "w") as f:
                json.dump(steps, f, indent=4)
```

---

### 5. Experience Reflection（经验反思阶段）

**输入（prompt_tokens）包括：**
- System prompt（系统提示）
- `prompt_knowledge_shortcuts`（快捷方式反思提示）
- `prompt_knowledge_tips`（提示信息反思提示）

**输出（completion_tokens）包括：**
- `new_shortcut`（新的快捷方式）
- `updated_tips`（更新的提示信息）

**代码位置：**
```784:824:Mobile-Agent-E/inference_agent_E.py
        ### Experience Reflection: Update Tips & Shortcuts for Self-Evolving ###
        if len(info_pool.action_outcomes) > 0:
            # at the end of each task, update the tips and shortcuts
            if "Finished" in info_pool.current_subgoal.strip():
                print("\n### Experience Reflector ... ###\n")
                experience_reflection_start_time = time.time()
                # shortcuts
                prompt_knowledge_shortcuts = exp_reflector_shortcuts.get_prompt(info_pool)
                chat_knowledge_shortcuts = exp_reflector_shortcuts.init_chat()
                chat_knowledge_shortcuts = add_response("user", prompt_knowledge_shortcuts, chat_knowledge_shortcuts, image=None)
                output_knowledge_shortcuts = get_reasoning_model_api_response(chat_knowledge_shortcuts, model=KNOWLEDGE_REFLECTION_MODEL, temperature=temperature)
                parsed_result_knowledge_shortcuts = exp_reflector_shortcuts.parse_response(output_knowledge_shortcuts)
                new_shortcut_str = parsed_result_knowledge_shortcuts['new_shortcut']
                if new_shortcut_str != "None" and new_shortcut_str is not None:
                    exp_reflector_shortcuts.add_new_shortcut(new_shortcut_str, info_pool)
                print("New Shortcut:", new_shortcut_str)
                # tips
                prompt_knowledge_tips = exp_reflector_tips.get_prompt(info_pool)
                chat_knowledge_tips = exp_reflector_tips.init_chat()
                chat_knowledge_tips = add_response("user", prompt_knowledge_tips, chat_knowledge_tips, image=None)
                output_knowledge_tips = get_reasoning_model_api_response(chat_knowledge_tips, model=KNOWLEDGE_REFLECTION_MODEL, temperature=temperature)
                parsed_result_knowledge_tips = exp_reflector_tips.parse_response(output_knowledge_tips)
                updated_tips = parsed_result_knowledge_tips['updated_tips']
                info_pool.tips = updated_tips
                print("Updated Tips:", updated_tips)

                prompt_knowledge = [prompt_knowledge_shortcuts, prompt_knowledge_tips]
                output_knowledge = [output_knowledge_shortcuts, output_knowledge_tips]
                
                experience_reflection_end_time = time.time()
                steps.append({
                    "step": iter,
                    "operation": "experience_reflection",
                    "prompt_knowledge": prompt_knowledge,
                    "raw_response": output_knowledge,
                    "new_shortcut": new_shortcut_str,
                    "updated_tips": updated_tips,
                    "duration": experience_reflection_end_time - experience_reflection_start_time,
                })
                with open(log_json_path, "w") as f:
                    json.dump(steps, f, indent=4)
```

---

## Token 记录方式

### 当前实现

Mobile-Agent-E 的 `inference_chat` 函数**只返回响应内容**，不返回 token 信息：

```55:182:Mobile-Agent-E/MobileAgentE/api.py
def inference_chat(chat, model, api_url, token, usage_tracking_jsonl = None, max_tokens = 2048, temperature = 0.0):
    # ... API 调用代码 ...
    res_content = res_json['choices'][0]['message']['content']
    if usage_tracking_jsonl:
        usage = track_usage(res_json, api_key=token)
        with open(usage_tracking_jsonl, "a") as f:
            f.write(json.dumps(usage) + "\n")
    
    return res_content  # 只返回内容，不返回 token 信息
```

### Token 信息记录位置

1. **如果设置了 `usage_tracking_jsonl`**：
   - Token 信息会记录到指定的 JSONL 文件中
   - 包含 `prompt_tokens`、`completion_tokens`、`total_tokens` 等信息

2. **在 `steps.json` 中**：
   - **当前不记录 token 信息**
   - 只记录 `prompt_planning`、`prompt_action`、`raw_response` 等文本内容

---

## 总结

### 每个阶段的 Token 分类

| 阶段 | 输入（prompt_tokens） | 输出（completion_tokens） |
|------|----------------------|--------------------------|
| **Planning** | `prompt_planning`（包括用户指令、快捷方式、截图） | `thought` + `plan` + `current_subgoal` |
| **Action** | `prompt_action`（包括用户指令、计划、屏幕信息、截图等） | `action_thought` + `action_object` + `action_description` |
| **Action Reflection** | `prompt_action_reflect`（包括用户指令、动作前后截图） | `outcome` + `error_description` + `progress_status` |
| **Notetaking** | `prompt_note`（包括用户指令、当前截图） | `important_notes` |
| **Experience Reflection** | `prompt_knowledge_shortcuts` + `prompt_knowledge_tips` | `new_shortcut` + `updated_tips` |

### 关键点

1. **`prompt_planning` 和 `prompt_action` 都是输入**，属于 `prompt_tokens`
2. **`action_thought` 是输出**，属于 `completion_tokens`（不是 `prompt_tokens`）
3. **每个阶段都有独立的 token 使用**，需要分别统计
4. **当前 `steps.json` 不记录 token 信息**，如需记录需要修改代码

---

## 与 Phone-Agent 的对比

| 项目 | 架构 | Token 记录 |
|------|------|-----------|
| **Mobile-Agent-E** | 多阶段（Planning → Action → Reflection → Notetaking） | 每个阶段独立记录，但当前 `steps.json` 不记录 token |
| **Phone-Agent** | 单阶段（Action with integrated thinking） | 记录 `prompt_tokens`（包括 `prompt_action`）和 `completion_tokens`（包括 `action_thought` + `action`） |




