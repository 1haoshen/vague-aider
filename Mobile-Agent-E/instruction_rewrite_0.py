# instruction_rewrite.py: 使用 Gemini-2.5-pro 模型补充用户指令，基于 app-data-2.json
# 参考 Mobile-Agent-E 项目（如 api.py 中的 API 调用和 Prompt 构建）
# 原因：实现查询功能，提供可运行脚本，便于扩展

import json
import os
import requests
import re  # 新增：用于关键词提取
import logging  # 新增：用于日志
import json_repair  # 新增：假设pip install json-repair
import unicodedata  # 新增：用于语言检测
import datetime  # 新增

import time  # 新增：用于耗时测量

logging.basicConfig(level=logging.DEBUG)  # 设置日志级别

# 默认路径（参考项目布局，可自定义）
APP_DATA_PATH = "D:/Mobile-Agent/MobileAgent-main/MobileAgent-main/app-data/cn-en-app-data-action-str.json"
GEMINI_MODEL = "google/gemini-2.0-flash-lite-001"  # 指定模型，使用OpenRouter支持的正确模型名称"google/gemini-2.0-flash-lite-001"
API_ENDPOINT = f"https://openrouter.ai/api/v1/chat/completions"

def load_app_data(file_path: str = APP_DATA_PATH) -> dict:
    """读取 app-data-2.json 文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"app-data-2.json 未找到于 {file_path}")
    except json.JSONDecodeError:
        raise ValueError("app-data-2.json 格式无效")

def detect_language(text: str) -> str:
    """检测输入语言：如果包含中文，返回'zh'；否则'en'"""
    for char in text:
        if unicodedata.category(char).startswith('Lo') and 'CJK' in unicodedata.name(char, ''):
            return 'zh'
    return 'en'

def build_prompt(user_instruction: str, app_data: dict, action_object_str: str = None) -> str:
    """构建 Prompt，注入 app-data-2.json 内容（核心版：意图驱动 + action_object_str匹配 + 完整操作轨迹）"""

    # 检测语言
    lang = detect_language(user_instruction)
    lang_instruction = "Output in English if the user input is in English, or in Chinese if in Chinese." if lang == 'en' else "如果用户输入是中文，则输出中文；如果是英文，则输出英文。"

    # 核心意图识别系统（基于优质生成结果分析）
    user_lower = user_instruction.lower()

    # 精确的任务意图映射（从优质结果中学习）
    core_intent_mapping = {
        # 记录/保存类意图 -> 笔记app
        'record': {
            'keywords': ['record', 'write', 'save', 'note', '备忘', '笔记', '记录', '保存', 'log', 'document', 'memo'],
            'target_apps': ['备忘录/笔记', '备忘录', '笔记', 'Notes', 'Memo'],
            'action_patterns': ['create note', 'save', 'record', 'write down']
        },

        # 搜索/查询类意图 -> 浏览器app
        'search': {
            'keywords': ['search', 'find', 'look', 'browse', 'query', '查询', '查找', '浏览', 'check', 'weather', 'forecast'],
            'target_apps': ['Google Chrome', '夸克', 'Chrome', 'Browser', '浏览器'],
            'action_patterns': ['search', 'query', 'find', 'browse']
        },

        # 规划/组织类意图 -> 旅行/规划app
        'plan': {
            'keywords': ['plan', 'schedule', 'organize', 'travel', 'trip', 'journey', '规划', '安排', '旅行', '行程'],
            'target_apps': ['Tripadvisor', 'Booking', '携程', '去哪儿', 'Maps', '地图'],
            'action_patterns': ['plan', 'schedule', 'organize', 'book', 'reserve']
        },

        # 社交/分享类意图 -> 社交app
        'share': {
            'keywords': ['share', 'send', 'post', 'message', '分享', '发送', '发布'],
            'target_apps': ['微信', 'WeChat', '微博', 'Twitter', 'Facebook'],
            'action_patterns': ['share', 'send', 'post', 'message']
        }
    }

    # 识别用户核心意图
    matched_intents = []
    for intent_name, intent_config in core_intent_mapping.items():
        if any(kw in user_lower for kw in intent_config['keywords']):
            matched_intents.append((intent_name, intent_config))

    # 如果没有匹配到意图，使用通用搜索意图
    if not matched_intents:
        matched_intents = [('search', core_intent_mapping['search'])]

    # 核心app匹配算法（基于意图 + action_object_str优先级）
    if not isinstance(app_data, list):
        filtered_apps = []
    else:
        app_candidates = []

        for app in app_data:
            if not isinstance(app, dict):
                continue

            app_name = app.get('app_name', '')
            app_name_lower = app_name.lower()
            action_object_str = app.get('action_object_str', {})

            # 核心匹配逻辑：基于意图直接匹配目标app
            total_score = 0
            matched_intents = []

            for intent_name, intent_config in matched_intents:
                # 检查是否是目标app
                target_apps = intent_config['target_apps']
                if any(target_app.lower() in app_name_lower for target_app in target_apps):
                    total_score += 100  # 直接目标app匹配，最高优先级
                    matched_intents.append(f"target_{intent_name}")

                # 检查action_object_str是否匹配意图模式
                elif isinstance(action_object_str, dict):
                    for action_key in action_object_str.keys():
                        action_key_lower = action_key.lower()
                        action_patterns = intent_config['action_patterns']
                        if any(pattern in action_key_lower for pattern in action_patterns):
                            total_score += 50  # action_object_str匹配，高优先级
                            matched_intents.append(f"action_{intent_name}")
                            break

                # 检查功能列表是否匹配
                common_functions = app.get('common_functions', [])
                for func in common_functions:
                    func_lower = func.lower()
                    action_patterns = intent_config['action_patterns']
                    if any(pattern in func_lower for pattern in action_patterns):
                        total_score += 30  # 功能匹配，中等优先级
                        matched_intents.append(f"function_{intent_name}")
                        break

            # 只有匹配上的app才进入候选列表
            if total_score > 0:
                app_candidates.append((total_score, {
                    'app_name': app_name,
                    'brief_introduction': app.get('brief_introduction', ''),
                    'common_functions': app.get('common_functions', []),
                    'action_object_str': action_object_str,  # 完整保留action_object_str
                    'matched_intents': matched_intents,
                    'match_score': total_score
                }))

        # 按匹配分数排序
        app_candidates.sort(reverse=True, key=lambda x: x[0])

        # 智能选择app组合（基于优质生成结果的学习）
        selected_apps = []

        # 策略1: 为每个意图选择最佳匹配的app
        intent_app_map = {}
        for score, app in app_candidates:
            for matched_intent in app['matched_intents']:
                intent_key = matched_intent.split('_')[1]  # 提取意图名称
                if intent_key not in intent_app_map or score > intent_app_map[intent_key][0]:
                    intent_app_map[intent_key] = (score, app)

        # 从intent_app_map中选择app，确保覆盖所有意图
        covered_intents = set()
        for intent_key, (score, app) in intent_app_map.items():
            if app['app_name'] not in [s['app_name'] for s in selected_apps]:
                selected_apps.append(app)
                covered_intents.add(intent_key)

            # 限制app数量，避免过度
            if len(selected_apps) >= 4:
                break

        # 策略2: 如果意图覆盖不全，补充高分app
        if len(selected_apps) < 3:
            for score, app in app_candidates[:5]:
                if app['app_name'] not in [s['app_name'] for s in selected_apps]:
                    selected_apps.append(app)
                    if len(selected_apps) >= 3:
                        break

        filtered_apps = selected_apps

    # 如果完全没有匹配，使用基于意图的默认app
    if not filtered_apps:
        default_app_map = {
            'record': {'name': '备忘录/笔记', 'fallback': ['备忘录', '笔记', 'Notes']},
            'search': {'name': 'Google Chrome', 'fallback': ['夸克', 'Chrome', 'Browser']},
            'plan': {'name': 'Tripadvisor', 'fallback': ['Booking', '携程', 'Maps']},
            'share': {'name': '微信', 'fallback': ['WeChat', '微博']}
        }

        default_apps = []
        for intent_name, intent_config in matched_intents:
            default_config = default_app_map.get(intent_name, default_app_map['search'])

            # 查找默认app
            for app in app_data:
                if isinstance(app, dict):
                    app_name = app.get('app_name', '')
                    if app_name == default_config['name'] or any(fallback in app_name for fallback in default_config['fallback']):
                        default_apps.append({
                            'app_name': app_name,
                            'brief_introduction': app.get('brief_introduction', ''),
                            'common_functions': app.get('common_functions', []),
                            'action_object_str': app.get('action_object_str', {}),
                            'matched_intents': [f"default_{intent_name}"],
                            'match_score': 20
                        })
                        break

        filtered_apps = default_apps[:3]  # 最多3个默认app

    # 完整app数据注入：确保action_object_str完整保留
    formatted_apps = []
    for app in filtered_apps:
        # 完整保留action_object_str，用于生成具体操作轨迹
        formatted_app = {
            'app_name': app['app_name'],
            'description': app['brief_introduction'],
            'functions': app['common_functions'],
            'action_object_str': app['action_object_str'],  # 完整保留action_object_str
            'matched_intents': app.get('matched_intents', [])
        }
        formatted_apps.append(formatted_app)

    # 优化JSON格式：减少token但保持可读性，确保中文正确显示
    app_data_str = json.dumps(formatted_apps, ensure_ascii=False, separators=(',', ':'))

    # 核心few-shot示例：基于优质生成结果，强调具体app名称和action_object_str操作轨迹
    few_shot = """
示例1 (多app协作 - 天气记录和旅行规划，基于优质生成结果):
用户指令: Please record the weather in Pittsburgh for the next three days and provide me with a travel plan.
app数据: [{"app_name":"Google Chrome","description":"Web browser for searching and browsing","functions":["网页搜索","信息查询"],"action_object_str":{}},{"app_name":"备忘录/笔记","description":"Note-taking app for recording information","functions":["创建笔记","搜索笔记"],"action_object_str":{"创建笔记":["open beiwanglu/biji app","tap the white plus sign in a yellow circle","type content","tap the icon of black correct symbol"]}},{"app_name":"Tripadvisor","description":"Travel planning and review platform","functions":["搜索地点","查看评价"],"action_object_str":{}}]
输出: {"level2_instruction": "Open Google Chrome to check the weather in Pittsburgh, then use the Notes app to record it, and finally use Tripadvisor to create a travel plan. (Involves browser, utility, and travel apps)", "level3_instruction": "Open the Google Chrome app, tap the search box and type 'weather in Pittsburgh for the next three days' to view the forecast. Then, open the Notes app, tap the white plus sign in a yellow circle to create a new note, and record the weather information, tap the icon of black correct symbol to save. Next, open the Tripadvisor app, tap the search icon, type 'Pittsburgh', and browse through 'Things to Do' and 'Restaurants' to create a travel plan. Finally, switch back to the Notes app to record the travel plan details.", "referenced_apps": ["Google Chrome", "备忘录/笔记", "Tripadvisor"], "reason": "Google Chrome for web search to check weather, Notes app for recording information using its note creation sequence, and Tripadvisor for travel planning based on location search functions"}

示例2 (基于action_object_str的具体操作轨迹):
用户指令: 创建一个新的笔记并记录今天的任务
app数据: [{"app_name":"备忘录/笔记","description":"Note-taking and task management app","functions":["创建笔记","添加待办"],"action_object_str":{"创建笔记":["open beiwanglu/biji app","tap the white plus sign in a yellow circle","type content of 'chuangjianbiji'","tap the icon of black correct symbol representing completion"],"添加待办":["open beiwanglu/biji app","tap the 'daiban' button at the bottom","tap the white plus sign in a yellow circle","type the to-do list","tap the 'wancheng' button in yellow"]}}]
输出: {"level2_instruction": "打开备忘录/笔记app创建新笔记并添加任务", "level3_instruction": "打开备忘录/笔记app，点击黄圈中的白色加号创建新笔记，输入笔记内容，点击黑色对勾图标完成保存。然后点击底部的'待办'按钮，点击黄圈中的白色加号，输入任务内容，点击黄色的'完成'按钮保存任务。", "referenced_apps": ["备忘录/笔记"], "reason": "使用备忘录/笔记app的action_sequences直接生成创建笔记和添加待办的具体操作步骤，包括UI元素定位和操作顺序"}

示例3 (跨app协作 - 搜索记录分享):
用户指令: 搜索餐厅信息并分享到微信
app数据: [{"app_name":"Google Chrome","description":"Web browser for information search","functions":["网页搜索"],"action_object_str":{}},{"app_name":"备忘录/笔记","description":"Note-taking app","functions":["创建笔记","分享笔记"],"action_object_str":{"分享笔记":["tap the share button with the arrow at the top","tap the choice 'yitupiangeshifenxiang'","tap the wechat icon","tap the search box","type the friend name","tap the search result","tap 'send' button"]}},{"app_name":"微信","description":"Social messaging app","functions":["发送消息"],"action_object_str":{}}]
输出: {"level2_instruction": "使用Google Chrome搜索餐厅信息，用备忘录/笔记记录，然后分享到微信", "level3_instruction": "打开Google Chrome，点击搜索框输入餐厅查询内容查看结果。然后打开备忘录/笔记app，点击黄圈白色加号创建笔记，输入餐厅信息后点击黑色对勾保存。接着点击顶部的箭头分享按钮，选择'以图片格式分享'，点击微信图标，点击搜索框输入好友姓名，点击搜索结果，点击绿色'发送'按钮完成分享。", "referenced_apps": ["Google Chrome", "备忘录/笔记", "微信"], "reason": "Google Chrome用于搜索餐厅信息，备忘录/笔记用于记录和分享（基于action_sequences的分享功能），微信用于社交分享，实现完整的信息获取-记录-分享流程"}
"""
    
    # 如果提供 action_object_str，注入到prompt中
    action_str = f"action_object_str: {action_object_str}\n" if action_object_str else ""

    prompt = (
        f"You are a mobile app instruction expert. Convert user requests into executable app operation sequences using EXACT app names and action_object_str from the knowledge base.\n\n"
        f"MANDATORY RULES (follow precisely):\n\n"
        f"1. APP NAME RULE:\n"
        f"   - ONLY use app names EXACTLY as they appear in the app data\n"
        f"   - Example: 'Google Chrome', '备忘录/笔记', 'Tripadvisor'\n"
        f"   - NEVER use generic terms\n\n"
        f"2. ACTION SEQUENCE RULE:\n"
        f"   - FIND and ADAPT action_object_str steps for relevant apps\n"
        f"   - CONVERT technical steps into natural mobile UI operations\n"
        f"   - Example: 'tap the white plus sign in a yellow circle' (from action sequence)\n\n"
        f"3. WORKFLOW RULE:\n"
        f"   - SEQUENCE: Open app → Perform operations → Switch to next app\n"
        f"   - Use 'Then, open [Exact App Name]' for transitions\n"
        f"   - Complete full task workflow\n\n"
        f"4. DETAIL RULE:\n"
        f"   - Include SPECIFIC UI elements and gestures\n"
        f"   - Reference actual app functions\n"
        f"   - Make executable on real devices\n\n"
        f"5. LANGUAGE: {lang_instruction}\n\n"
        f"APP KNOWLEDGE BASE (use exact names and action_object_str):\n{app_data_str}\n\n"
        f"{action_str}"
        f"USER INSTRUCTION: {user_instruction}\n\n"
        f"REQUIRED OUTPUT FORMAT (JSON only):\n"
        f"{{\n"
        f"  \"level2_instruction\": \"Brief summary with exact app names\",\n"
        f"  \"level3_instruction\": \"Step-by-step UI operations with app switching\",\n"
        f"  \"referenced_apps\": [\"Exact names from knowledge base\"],\n"
        f"  \"reason\": \"How app functions and action sequences fulfill the task\"\n"
        f"}}\n\n"
        f"PERFECT EXAMPLES (emulate these exactly):\n{few_shot}"
    )
    return prompt

def call_gemini(prompt: str) -> tuple[str, dict]:
    """调用 Gemini API，并返回文本 + usage"""
    api_key = os.getenv("GEMINI_API_KEY") or "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"  # 从环境变量获取，或使用默认（OpenRouter key）
    if not api_key:
        raise ValueError("GEMINI_API_KEY 未设置，请在环境变量中设置")

    payload = {
        "model": GEMINI_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 4096,  # 增加到4096
        "temperature": 0.0  # 低温度，确保确定性（参考 E 项目）
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"  # 使用 Bearer Token，匹配 OpenAI 兼容端点
    }

    try:
        response = requests.post(API_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        generated_text = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})  # 提取 usage
        logging.info(f"Token usage: {usage}")
        return generated_text, usage
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Gemini API 请求失败: {e}")
    except (KeyError, IndexError):
        raise ValueError("Gemini API 响应格式无效")

# 更新解析以匹配新输出结构
def rewrite_instruction(user_instruction: str, action_object_str: str = None, save_to_file: str = None) -> dict:  # 修改返回类型为dict
    """主函数：补充用户指令（支持多级和action_object_str）"""
    start_time = time.time()  # 开始计时
    app_data = load_app_data()
    prompt = build_prompt(user_instruction, app_data, action_object_str)
    
    # 新增：验证action_object_str
    if action_object_str:
        try:
            json.loads(action_object_str)
        except json.JSONDecodeError:
            logging.warning("无效action_object_str，回退到None")
            action_object_str = None

    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for attempt in range(3):  # 新增：重试机制，最多3次
        response, usage = call_gemini(prompt)  # 修改为接收 usage
        # 累加 usage
        for key in total_usage:
            total_usage[key] += usage.get(key, 0)
        
        # 新增：清理markdown/code blocks
        response = response.strip().strip('```json').strip('```').strip()
        
        # 增强修复：使用json_repair
        try:
            parsed = json_repair.loads(response)
        except Exception as e:
            logging.debug(f"修复失败: {str(e)}")
            parsed = None
        
        if parsed and 'level2_instruction' in parsed and 'level3_instruction' in parsed:
            duration = time.time() - start_time  # 计算耗时
            result = {
                "original_instruction": user_instruction,
                "level2_instruction": parsed['level2_instruction'],
                "level3_instruction": parsed['level3_instruction'],
                "referenced_apps": parsed['referenced_apps'],
                "reason": parsed['reason'],
                "model": GEMINI_MODEL,  # 添加调用的模型名称
                "token_usage": total_usage,  # 添加
                "duration_seconds": duration  # 添加
            }
            # 新增：日志是否使用了action_object_str
            if action_object_str:
                logging.info("Level 3使用了提供的action_object_str")
            else:
                logging.info("Level 3回退到通用JSON逻辑")
            if save_to_file:
                # 新增：读取现有文件或初始化list, 追加result, 写入
                history = []
                if os.path.exists(save_to_file):
                    with open(save_to_file, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                        if not isinstance(history, list):
                            history = [history]  # 如果不是list, 转换为list
                    # 新增：为历史item添加id如果缺失
                    for i, item in enumerate(history):
                        if 'id' not in item:
                            item['id'] = i + 1
                        if 'timestamp' not in item:
                            item['timestamp'] = datetime.datetime.now().isoformat()  # 添加时间戳
                # 新增：为新result添加id和timestamp
                result['id'] = len(history) + 1
                result['timestamp'] = datetime.datetime.now().isoformat()
                history.append(result)
                with open(save_to_file, 'w', encoding='utf-8') as f:
                    json.dump(history, f, indent=4, ensure_ascii=False)
                logging.info(f"追加到历史并保存到 {save_to_file}")
            return result
        else:
            logging.warning("响应不完整或JSON格式错误: " + response)
            continue  # 重试而不是立即返回
    
    duration = time.time() - start_time
    return {"error": "所有重试失败", "duration_seconds": duration, "token_usage": total_usage}  # 如果循环结束仍失败

# 示例使用（优化测试）
if __name__ == "__main__":
    # 测试指令：天气查询，应该匹配浏览器或天气app
    user_input = "Please record the weather in Pittsburgh for the next three days and provide me with a travel plan."
    example_action_str = '{"action": ["open", "search", "record"], "object": ["weather app", "search box", "results"], "path": "open weather app > search location > record forecast", "app": ["weather", "browser"]}'

    try:
        print("=== 测试优化后的指令改写 ===")
        print(f"用户指令: {user_input}")
        print(f"Action Object String: {example_action_str}")
        print()

        # 执行一次测试
        result = rewrite_instruction(user_input, example_action_str, save_to_file="output_rewrite_0.json")

        if "error" in result:
            print(f"错误: {result['error']}")
        else:
            print("结果:")
            print(f"  2级指令: {result['level2_instruction']}")
            print(f"  3级指令: {result['level3_instruction']}")
            print(f"  引用app: {result['referenced_apps']}")
            print(f"  理由: {result['reason']}")
            print(f"  模型: {result['model']}")
            print(f"  Token消耗: {result['token_usage']}")
            print(f"  耗时: {result['duration_seconds']:.2f}秒")

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
