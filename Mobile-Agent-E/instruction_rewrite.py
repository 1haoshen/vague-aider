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
APP_DATA_PATH = "../app-data/cn-en-app-data-action-str.json"
GEMINI_MODEL = "gemini-2.5-pro"  # 指定模型
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
    """构建 Prompt，注入 app-data-2.json 内容（增强版：动态提取 + 过滤 + 多级改写）"""
    # 新增：检测语言
    lang = detect_language(user_instruction)
    lang_instruction = "Output in English if the user input is in English, or in Chinese if in Chinese." if lang == 'en' else "如果用户输入是中文，则输出中文；如果是英文，则输出英文。"

    # 新增：从指令提取关键词（简单NLP）
    keywords = re.findall(r'\w+', user_instruction.lower())  # 提取单词

    # 增强过滤：匹配appname并提取键值
    if not isinstance(app_data, list):
        filtered_apps = []
    else:
        filtered_apps = [
            {'appname': app.get('appname'), 'description': app.get('description'), 'functions': app.get('functions')}  # 只提取关键字段
            for app in app_data 
            if isinstance(app, dict) and any(kw in app.get('appname', '').lower() for kw in keywords)
        ]
    filtered_apps = filtered_apps[:3]  # 限制top 3减少长度
    app_data_str = json.dumps(filtered_apps or app_data, indent=2, ensure_ascii=False)

    # 增强few-shot：添加链式推理指导，并示例多级输出（添加双语示例支持）
    few_shot = """
# 示例1 (English):
# 用户指令: Open WeChat
# app-data-2.json 数据: [{"appname": "WeChat", "description": "Chat app", "functions": ["Send message"]}]
# action_object_str: {"action": "open", "object": "chat"}
# 输出: {'level2_instruction': 'Open WeChat app (involves chat app)', 'level3_instruction': 'Open WeChat app, enter chat interface and send message (based on functions path)', 'referenced_apps': ['WeChat'], 'reason': 'Based on functions to generate path description'}

# 示例1 (中文):
# 用户指令: 打开微信
# app-data-2.json 数据: [{"appname": "微信", "description": "聊天app", "functions": ["发送消息"]}]
# action_object_str: {"action": "open", "object": "chat"}
# 输出: {'level2_instruction': '打开微信app（涉及聊天app）', 'level3_instruction': '打开微信app, 进入聊天界面发送消息（基于functions路径）', 'referenced_apps': ['微信'], 'reason': '基于functions生成路径描述'}

# 示例2:
# 用户指令: 查找商品
# app-data-2.json 数据: [{"appname": "淘宝", "description": "电商app", "functions": ["搜索商品"]}]
# action_object_str: {"action": "search", "object": "product"}
# 输出: {'level2_instruction': '打开淘宝app（涉及电商app）', 'level3_instruction': '打开淘宝app, 点击搜索栏输入商品名称（基于functions路径）', 'referenced_apps': ['淘宝'], 'reason': '参考description和functions补充路径细节'}

# 示例3 (多app通信 + 多action路径):
# 用户指令: 分享歌曲到微信
# app-data-2.json 数据: [{"appname": "网易云音乐", "description": "在线音乐app", "functions": ["分享歌曲"], "action_object_str": {"分享歌曲": ["open netease cloud app", "tap search box", "type song name", "tap play button", "tap ellipsis", "tap share", "tap wechat icon", "tap search friend", "type friend name", "tap send"]}}, {"appname": "微信", "description": "社交app", "functions": ["发送消息"]}]
# action_object_str: {"actions": ["search", "play", "share"], "objects": ["song", "button", "friend"], "path": "open music app > search and play song > share to wechat > search friend > send", "app": ["netease cloud music", "wechat"]}
# 输出: {'level2_instruction': '打开网易云音乐app分享歌曲到微信app（涉及音乐和社交app）', 'level3_instruction': '打开网易云音乐app, 点击搜索框输入歌曲名称, 点击播放按钮, 点击省略号图标选择分享, 点击微信图标切换到微信app, 搜索好友名称并发送（基于网易云的分享歌曲路径和微信函数, 实现app间通信）', 'referenced_apps': ['网易云音乐', '微信'], 'reason': '结合网易云的action_object_str多步骤路径（search/play/share）和微信函数, 实现跨app分享通信'}

# 示例4 (边缘 + 详细路径描述):
# 用户指令: 处理未知app
# app-data-2.json 数据: []  # 无匹配
# action_object_str: null
# 输出: {'level2_instruction': '尝试打开默认app（无特定app）', 'level3_instruction': '尝试打开默认app处理（无路径描述）', 'referenced_apps': [], 'reason': '无匹配app, 回退默认'}

# 示例5 (复杂多action + app通信):
# 用户指令: 在美图秀秀美颜自拍照后分享到微信
# app-data-2.json 数据: [{"appname": "美图秀秀", "description": "美颜相机app", "functions": ["一键美颜人像"], "action_object_str": {"一键美颜人像": ["open meituxiuxiu app", "tap Renxiangmeirong", "tap profile picture", "tap yijianmeiyan", "tap filter", "tap checkmark", "tap save"]}}, {"appname": "微信", "description": "社交app", "functions": ["发送消息"], "action_object_str": {"发送消息": ["open wechat app", "tap search", "type friend name", "tap friend", "tap input bar", "type message", "tap send"]}}]
# action_object_str: {"actions": ["open", "tap", "save", "share"], "objects": ["profile picture", "filter", "button", "friend"], "path": "open meituxiuxiu > beautify photo > save > share to wechat > search friend > send", "app": ["meituxiuxiu", "wechat"]}
# 输出: {'level2_instruction': '打开美图秀秀app美颜自拍照并分享到微信app（涉及美颜和社交app）', 'level3_instruction': '打开美图秀秀app, 点击人像美颜选择自拍照, 点击一键美颜应用滤镜, 点击保存, 然后分享到微信app, 搜索好友名称进入聊天, 点击输入栏发送照片（基于美图秀秀的一键美颜人像路径和微信的发送消息功能, 实现app间通信和路径链式描述）', 'referenced_apps': ['美图秀秀', '微信'], 'reason': '迭代action_object_str的多action (open/tap/save/share) 和路径, 结合JSON functions生成详细跨app流程'}

# 示例6 (多app比价 + 迭代引用app):
# 用户指令: 帮我将一款性价比高的香水加入购物车
# app-data-2.json 数据: [{"appname": "淘宝", "description": "电商app", "functions": ["商品搜索", "将商品加入购物车"]}, {"appname": "京东", "description": "电商app", "functions": ["商品搜索", "将商品加入购物车"]}, {"appname": "拼多多", "description": "电商app", "functions": ["商品搜索", "将商品加入购物车"]}]
# action_object_str: {"action": "search and compare", "object": "perfume", "path": "search in each app > compare prices > add to cart in best app"}
# 输出: {'level2_instruction': '打开淘宝/京东/拼多多app进行搜索比价并加入购物车（涉及电商app）', 'level3_instruction': '依次打开淘宝、京东、拼多多app, 点击顶部搜索栏输入“性价比高的香水”并点击搜索, 在结果列表中查看商品详情和价格, 记录多个app的结果信息后找到性价比最高的香水, 然后在对应app中点击加入购物车按钮（基于functions的商品搜索和加入购物车, 实现多app比价）', 'referenced_apps': ['淘宝', '京东', '拼多多'], 'reason': '用户需求涉及比价, 迭代引用app执行搜索/比较, 然后在最佳app完成加入购物车'}

# 示例7 (处理模糊对象，如视频博主):
# 用户指令: 关注'向前的赵'
# app-data-2.json 数据: [{"appname": "哔哩哔哩", "description": "视频app", "functions": ["关注用户"], "action_object_str": {"关注用户": ["open bilibili app", "tap search box", "type user name", "tap user profile", "tap follow button"]}}, {"appname": "网易云音乐", "description": "音乐app", "functions": ["关注歌手"]}]
# action_object_str: null
# 输出: {'level2_instruction': '先使用浏览器搜索用户名称, 然后打开相应app关注（涉及视频/音乐app）', 'level3_instruction': '打开浏览器如Google Chrome、夸克等, 搜索“向前的赵”, 确定用户所在平台, 根据搜索结果然后打开对应app（bilibili/TikTok/X/Facebook）, 点击搜索框输入“向前的赵”, 在搜索结果中点击用户主页, 点击关注按钮（基于哔哩哔哩的关注用户路径）', 'referenced_apps': ['浏览器', '哔哩哔哩'], 'reason': '指令涉及未知用户, 先通过浏览器检索上下文为视频平台, 优先匹配哔哩哔哩而非音乐app, 根据functions生成路径'}
"""
    # 如果提供 action_object_str，注入到prompt中
    action_str = f"action_object_str: {action_object_str}\n" if action_object_str else ""

    prompt = (
        f"You are an instruction rewriting assistant. First match relevant apps from app-data-2.json based on appname, generate level 2 instruction (summary of apps and operations involved). Then based on action_object_str reference description and functions to generate level 3 instruction (description of app function paths). If involving multiple apps (e.g., comparison), open each app sequentially to perform operations (e.g., search, compare), and complete the action in the final app (e.g., add to cart). If no match, use general logic. Keep output concise but do not omit key operation paths and object descriptions, ensure JSON is complete. {lang_instruction}\n\n"  # 更新: 添加语言指导
        + few_shot + "\n\n"
        "app-data-2.json 数据：\n" + app_data_str + "\n\n"
        + action_str +
        "用户指令：" + user_instruction + "\n\n"
        "输出：JSON格式，包括{'level2_instruction': '2级指令', 'level3_instruction': '3级指令', 'referenced_apps': ['引用的appname'], 'reason': '简要理由'}"
    )
    return prompt

def call_gemini(prompt: str) -> tuple[str, dict]:
    api_key = os.getenv("GEMINI_API_KEY") or ""  # 从环境变量获取，或使用默认（测试用）
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
    #主函数：补充用户指令（支持多级和action_object_str）
    
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

# 示例使用（添加action_object_str示例）  
if __name__ == "__main__":
    user_input =  "Find a highly-rated historical biography on a community platform and added it to my cart."
     # 示例用户指令 帮我推荐一个获得多方好评的广州旅游景点
    example_action_str = '{"action": ["open", "tap", "type"], "object": ["search box", "button","text button","icon"], "path": "open app > tap search > type name", "app": ["netease cloud music","wechat"]}'  # 修复为有效JSON
    try:
        # 模拟两次执行
        for i in range(2):
            result = rewrite_instruction(user_input, example_action_str, save_to_file="output.json")
            if "error" in result:
                print(f"Run {i+1} 错误: {result['error']}")
            else:
                print(f"Run {i+1} 原指令:", result["original_instruction"])
                print(f"Run {i+1} 补充后的2级指令:", result["level2_instruction"])
                print(f"Run {i+1} 最终的补充指令:", result["level3_instruction"])
                print(f"Run {i+1} 引用app:", result["referenced_apps"])
                print(f"Run {i+1} 理由:", result["reason"])
                print(f"Run {i+1} Token Usage:", result["token_usage"])
                print(f"Run {i+1} Duration: {result['duration_seconds']} seconds")  # 添加打印
    except Exception as e:
        print(f"错误: {e}")
