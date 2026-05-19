# LLM-rewrite.py: 使用 Gemini-1.5-pro 模型补充用户指令，基于模型的通用能力
# 参考 instruction_rewrite.py 的结构，但不注入任何外部 JSON 数据

import json
import os
import requests
import re  # 用于关键词提取
import logging  # 用于日志
import json_repair  # 假设 pip install json-repair
import unicodedata  # 用于语言检测
import datetime
import time  # 用于耗时测量

logging.basicConfig(level=logging.DEBUG)  # 设置日志级别

GEMINI_MODEL = "gemini-2.5-pro"  # 指定模型
API_ENDPOINT = "https://yunwu.ai/v1/chat/completions"

def detect_language(text: str) -> str:
    """检测输入语言：如果包含中文，返回'zh'；否则'en'"""
    for char in text:
        if unicodedata.category(char).startswith('Lo') and 'CJK' in unicodedata.name(char, ''):
            return 'zh'
    return 'en'

def build_prompt(user_instruction: str) -> str:
    """构建 Prompt，使用模型的通用能力进行多级改写"""
    # 检测语言
    lang = detect_language(user_instruction)
    lang_instruction = "Output in English if the user input is in English, or in Chinese if in Chinese." if lang == 'en' else "如果用户输入是中文，则输出中文；如果是英文，则输出英文。"

    # 增强 few-shot 示例，支持双语和多级输出
    few_shot = """
示例1 (English):
用户指令: Open WeChat
输出: {'level2_instruction': 'Open WeChat app (involves chat app)', 'level3_instruction': 'Open WeChat app, enter chat interface and send message', 'referenced_apps': ['WeChat'], 'reason': 'Based on general knowledge of app functions to generate path description'}

示例1 (中文):
用户指令: 打开微信
输出: {'level2_instruction': '打开微信app（涉及聊天app）', 'level3_instruction': '打开微信app，进入聊天界面发送消息', 'referenced_apps': ['微信'], 'reason': '基于app通用功能生成路径描述'}

示例2:
用户指令: 查找商品
输出: {'level2_instruction': '打开电商app进行搜索', 'level3_instruction': '打开电商app，点击搜索栏输入商品名称', 'referenced_apps': ['淘宝'], 'reason': '参考通用电商流程补充路径细节'}

示例3 (多app通信 + 多action路径):
用户指令: 分享歌曲到微信
输出: {'level2_instruction': '打开音乐app分享歌曲到微信app（涉及音乐和社交app）', 'level3_instruction': '打开音乐app，搜索歌曲并播放，选择分享到微信，切换到微信app搜索好友并发送', 'referenced_apps': ['网易云音乐', '微信'], 'reason': '结合通用音乐和社交app流程，实现跨app分享'}

示例4 (边缘 + 详细路径描述):
用户指令: 处理未知app
输出: {'level2_instruction': '尝试打开默认app（无特定app）', 'level3_instruction': '尝试打开默认app处理（无路径描述）', 'referenced_apps': [], 'reason': '无匹配app，回退默认'}

示例5 (复杂多action + app通信):
用户指令: 在美图秀秀美颜自拍照后分享到微信
输出: {'level2_instruction': '打开美图秀秀app美颜自拍照并分享到微信app（涉及美颜和社交app）', 'level3_instruction': '打开美图秀秀app，选择自拍照应用美颜和滤镜，保存并分享到微信app，搜索好友发送', 'referenced_apps': ['美图秀秀', '微信'], 'reason': '基于通用美颜和社交app流程，实现跨app通信'}

示例6 (多app比价 + 迭代引用app):
用户指令: 帮我将一款性价比高的香水加入购物车
输出: {'level2_instruction': '打开多个电商app进行搜索比价并加入购物车（涉及电商app）', 'level3_instruction': '依次打开电商app，搜索“性价比高的香水”，比较价格后在最佳app加入购物车', 'referenced_apps': ['淘宝', '京东', '拼多多'], 'reason': '用户需求涉及比价，迭代引用app执行搜索/比较，然后完成加入购物车'}

示例7 (处理模糊对象，如视频博主):
用户指令: 关注'向前的赵'
输出: {'level2_instruction': '先搜索用户名称，然后打开相应app关注（涉及视频/音乐app）', 'level3_instruction': '打开浏览器搜索“向前的赵”，确定平台后打开对应app搜索并关注', 'referenced_apps': ['浏览器', '哔哩哔哩'], 'reason': '指令涉及未知用户，先通过浏览器检索，优先匹配视频app'}
"""

    prompt = (
        f"You are an instruction rewriting assistant. Generate level 2 instruction (summary of operations involved). Then generate level 3 instruction (description of function paths) based on general knowledge. If involving multiple apps (e.g., comparison), open each app sequentially to perform operations. If no match, use general logic. Keep output concise but do not omit key operation paths and object descriptions, ensure JSON is complete. {lang_instruction}\n\n"
        + few_shot + "\n\n"
        "用户指令：" + user_instruction + "\n\n"
        "输出：JSON格式，包括{'level2_instruction': '2级指令', 'level3_instruction': '3级指令', 'referenced_apps': ['引用的appname'], 'reason': '简要理由'}"
    )
    return prompt

def call_gemini(prompt: str) -> tuple[str, dict]:
    """调用 Gemini API，并返回文本 + usage"""
    api_key = os.getenv("GEMINI_API_KEY") or "sk-BAO0wS03Fb1KzKKXrGbbaHBGqolfc0jiKXqJAbljdXVyLDuy"  # 从环境变量获取，或使用默认
    if not api_key:
        raise ValueError("GEMINI_API_KEY 未设置，请在环境变量中设置")

    payload = {
        "model": GEMINI_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 4096,
        "temperature": 0.0
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    try:
        response = requests.post(API_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        generated_text = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        logging.info(f"Token usage: {usage}")
        return generated_text, usage
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Gemini API 请求失败: {e}")
    except (KeyError, IndexError):
        raise ValueError("Gemini API 响应格式无效")

def rewrite_instruction(user_instruction: str, save_to_file: str = None) -> dict:
    """主函数：补充用户指令（支持多级）"""
    start_time = time.time()
    prompt = build_prompt(user_instruction)
    
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for attempt in range(3):
        response, usage = call_gemini(prompt)
        for key in total_usage:
            total_usage[key] += usage.get(key, 0)
        
        response = response.strip().strip('```json').strip('```').strip()
        
        try:
            parsed = json_repair.loads(response)
        except Exception as e:
            logging.debug(f"修复失败: {str(e)}")
            parsed = None
        
        if parsed and 'level2_instruction' in parsed and 'level3_instruction' in parsed:
            duration = time.time() - start_time
            result = {
                "original_instruction": user_instruction,
                "level2_instruction": parsed['level2_instruction'],
                "level3_instruction": parsed['level3_instruction'],
                "referenced_apps": parsed.get('referenced_apps', []),
                "reason": parsed['reason'],
                "token_usage": total_usage,
                "duration_seconds": duration
            }
            if save_to_file:
                history = []
                if os.path.exists(save_to_file):
                    with open(save_to_file, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                        if not isinstance(history, list):
                            history = [history]
                    for i, item in enumerate(history):
                        if 'id' not in item:
                            item['id'] = i + 1
                        if 'timestamp' not in item:
                            item['timestamp'] = datetime.datetime.now().isoformat()
                result['id'] = len(history) + 1
                result['timestamp'] = datetime.datetime.now().isoformat()
                history.append(result)
                with open(save_to_file, 'w', encoding='utf-8') as f:
                    json.dump(history, f, indent=4, ensure_ascii=False)
                logging.info(f"追加到历史并保存到 {save_to_file}")
            return result
        else:
            logging.warning("响应不完整或JSON格式错误: " + response)
            continue
    
    duration = time.time() - start_time
    return {"error": "所有重试失败", "duration_seconds": duration, "token_usage": total_usage}

if __name__ == "__main__":
    user_input = "帮我推荐一款性价比高的枕头"
    try:
        for i in range(2):
            result = rewrite_instruction(user_input, save_to_file="output.json")
            if "error" in result:
                print(f"Run {i+1} 错误: {result['error']}")
            else:
                print(f"Run {i+1} 原指令:", result["original_instruction"])
                print(f"Run {i+1} 补充后的2级指令:", result["level2_instruction"])
                print(f"Run {i+1} 最终的补充指令:", result["level3_instruction"])
                print(f"Run {i+1} 引用app:", result["referenced_apps"])
                print(f"Run {i+1} 理由:", result["reason"])
                print(f"Run {i+1} Token Usage:", result["token_usage"])
                print(f"Run {i+1} Duration: {result['duration_seconds']} seconds")
    except Exception as e:
        print(f"错误: {e}")
