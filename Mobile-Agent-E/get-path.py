
import json
import time
import os
from datetime import datetime
import requests
import sys
import argparse
import logging
import json_repair

# 配置Gemini API密钥（请替换为实际密钥）
# genai.configure(api_key="sk-BAO0wS03Fb1KzKKXrGbbaHBGqolfc0jiKXqJAbljdXVyLDuy")  # 请替换为您的API密钥

# 定义模型
# model = genai.GenerativeModel('gemini-2.5-pro')  # 使用gemini-2.5-pro模型

logging.basicConfig(level=logging.DEBUG)

def build_prompt(path_ins_data):
    """
    构建prompt，使用fewshot示例，将path-ins.json中的信息转换为cn-en-app-data-action-str.json风格的action-object-str。
    """
    # Few-shot示例：展示从日志到模板的转换
    fewshot_examples = """
    示例输入（path-ins.json片段）：
    {
        "step": 2,
        "action_object_str": "{\"name\":\"Tap_Type_and_Enter\", \"arguments\":{\"x\":631, \"y\":224, \"text\":\"张惠妹 掉了\"}}",
        "action_description": "I will tap the search bar, type \"张惠妹 掉了\" (A-mei's \"Fallen\"), and press enter to search for the song.",
        "action_thought": "The user wants me to search for and play the song \"掉了\" by \"张惠妹\" in NetEase Cloud Music. ...",
        "current_subgoal": "在网易云音乐中搜索并播放张惠妹的歌曲《掉了》。"
    }

    示例输出（cn-en-app-data-action-str.json风格）：
    "歌曲搜索":[
        "open netease cloud app",
        "tap search box at the top",
        "type the 'song name'",
        "tap the 'search' result"
    ]

    现在，基于提供的path-ins.json数据，提取所有步骤的"action_object_str"、"action_description"、"action_thought"、"current_subgoal"信息，综合转换为类似上述的action-object-str格式。
    - 指定app名称：从数据推断为"网易云音乐"。
    - 涉及功能：从subgoal推断，如"歌曲搜索"、"播放音乐"、"添加歌单"、"分享歌曲"。
    - 生成明确的action（如tap、type、swipe），必要的action对象（如icon box button），action对象的特征描述（如icon的颜色、位置、组成，如"tap the play button like black triangle on yellow circle background"）。
    - 输出为一个对象，键为功能名称，值为字符串数组。
    """
    
    # 将path_ins_data转换为字符串以包含在prompt中
    path_ins_str = json.dumps(path_ins_data, ensure_ascii=False)
    
    # Additional Few-shot example with full structure
    full_example = """
    示例输出（完整app对象，类似cn-en-app-data-action-str.json）：
    {
        "id": 14,
        "app_name": "网易云音乐",
        "brief_introduction": "在线音乐类应用，拥有 1.8 亿首歌曲，具备 “小灯府上镜”“如视现场的歌词动效”“船舰助手” 等功能，提升音乐体验。",
        "icon_description": "红色背景，带有白色音符形状的标志，简洁易识别，传递音乐平台的文艺与活力。",
        "ui_description": " ",
        "common_functions": ["歌曲搜索", "播放音乐", "创建歌单", "分享歌曲", "关注用户", "下载歌曲", "发布笔记", "歌曲评论", "个性化推荐", "演唱会票务"],
        "action_object_str": {
            "歌曲搜索": ["open netease cloud app", "tap search box at the top", "type the 'song name'", "tap the 'search' result"],
            "播放音乐": ["open netease cloud app", "tap the play button like black triangle on yellow circle background"],
            "创建歌单": ["open netease cloud app", "tap the '+' button in the bottom right corner", "type the '歌单名称'", "tap the '创建' button"],
            "分享歌曲": ["open netease cloud app", "tap the '分享' button", "select '复制链接' or '分享到'"],
            "关注用户": ["open netease cloud app", "tap the '+' button in the top right corner", "search for the user", "tap '关注'"],
            "下载歌曲": ["open netease cloud app", "tap the '下载' button", "select '下载全部' or '下载单曲'"],
            "发布笔记": ["open netease cloud app", "tap the '+' button in the bottom right corner", "type the '笔记内容'", "tap the '发布' button"],
            "歌曲评论": ["open netease cloud app", "tap the '评论' button", "type the '评论内容'", "tap the '发送' button"],
            "个性化推荐": ["open netease cloud app", "tap the '推荐' button", "select '个性化推荐'"],
            "演唱会票务": ["open netease cloud app", "tap the '票务' button", "select '演唱会'"]
        }
    }

    生成时，输出类似上述完整app对象的JSON数组，基于path-ins.json推断app_name、brief_introduction、icon_description、common_functions，并生成action_object_str。
    """

    prompt = f"""
    {fewshot_examples}
    {full_example}

    输入path-ins.json数据：
    {path_ins_str}

    生成输出：
    """
    return prompt

def generate_action_object_str(path_ins_file):
    """
    读取path-ins.json，调用模型生成action-object-str，并返回结果。
    """
    with open(path_ins_file, 'r', encoding='utf-8') as f:
        path_ins_data = json.load(f)
    
    prompt = build_prompt(path_ins_data)
    
    start_time = time.time()
    API_ENDPOINT = "https://yunwu.ai/v1/chat/completions"
    api_key = "sk-BAO0wS03Fb1KzKKXrGbbaHBGqolfc0jiKXqJAbljdXVyLDuy"
    
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    payload = {
        "model": "gemini-2.5-pro",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 8192,
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
        print(f"API Response: {result}")
        generated_content = result["choices"][0]["message"]["content"]
        print(f"Generated Content: {generated_content}")
        usage = result.get("usage", usage)
    except Exception as e:
        logging.error(f"API call failed: {e}")
        return {"error": str(e)}
    
    # 解析生成的content（假设是JSON对象）
    try:
        generated_apps = json_repair.loads(generated_content)
        if not isinstance(generated_apps, list):
            generated_apps = [generated_apps]
        if not generated_apps:
            logging.warning("Empty generated_apps after parsing")
    except Exception as e:
        logging.error(f"Parsing failed: {e}")
        generated_apps = []
    
    # 构建输出结构，参考app-ins.json
    output = {
        "query": "从path-ins.json提取并转换action-object-str",
        "generated_apps": generated_apps,
        "token_usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        },
        "duration_seconds": time.time() - start_time,
        "timestamp": datetime.now().isoformat(),
        "id": len([f for f in os.listdir(os.path.dirname(path_ins_file)) if f.endswith('.json')]) + 1  # Count based on input dir
    }
    
    return output

def save_output(output, output_file):
    """
    保存输出到JSON文件，参考app-ins.json格式（追加到数组）。
    """
    output_dir = os.path.dirname(output_file)
    os.makedirs(output_dir, exist_ok=True)
    # Since output now has generated_apps as list, flatten and append to history array
    history = []
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
    history.extend(output["generated_apps"])
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process path-ins.json")
    parser.add_argument("log_dir", type=str, help="Directory containing path-ins.json")
    
    args = parser.parse_args()
    
    input_path = os.path.join(args.log_dir, "path-ins.json")
    output_path = os.path.join(args.log_dir, "processed-path-ins.json")
    
    output = generate_action_object_str(input_path)
    save_output(output, output_file=output_path)
    print(f"Processed and saved to {output_path}")
