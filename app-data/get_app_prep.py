# get_app_prep.py: Tool to Generate App Data for Building JSON Files

import json
import os
import requests
import re
import logging
import json_repair
import unicodedata
import datetime
import time
import sys

logging.basicConfig(level=logging.DEBUG)

# Default model and endpoint (no data path, as we don't load external JSON)
GEMINI_MODEL = "gemini-2.5-pro"
API_ENDPOINT = "https://yunwu.ai/v1/chat/completions"

def detect_language(text: str) -> str:
    """Detect language: 'zh' if Chinese characters are present, else 'en'."""
    for char in text:
        if unicodedata.category(char).startswith('Lo') and 'CJK' in unicodedata.name(char, ''):
            return 'zh'
    return 'en'

def build_prompt(user_query: str) -> str:
    """Build prompt using only Few-Shot examples, without external data injection."""
    lang = detect_language(user_query)
    lang_instruction = "Output in English if the query is in English, or in Chinese if in Chinese." if lang == 'en' else "如果查询是中文，则输出中文；如果是英文，则输出英文。"

    # Few-Shot examples for pure generation (no app_data_str)
    few_shot = """
Example 1 (English Query):
Query: Recommend a chat app
Output: [{"app_name": "X", "description": "A social media platform rated 4.0 stars, formerly known as Twitter. It features short-form posts, user following, and real-time conversations; supports trends, polls, and multimedia sharing.", "icon_description": "A black square icon with a white 'X' symbol", "common_functions": ["Search for information","Post a new tweet","Follow users","Retweet posts","Like posts","Comment on posts","Save posts to favorites","View trending topics","Check recent news highlights","Join group communities and share","Grok inquiries"]}]

Example 2 (Chinese Query):
Query: 推荐一个聊天app
Output: [{"app_name": "微信", "description": "一款广受欢迎的社交应用，可用于好友聊天社交，支持消息列表管理、群聊互动以及语音输入等功能，方便用户日常沟通交流。", "icon_description": "绿色气泡图标带有两个白色聊天符号", "common_functions": ["发送文本消息", "进行语音通话", "分享朋友圈",扫码支付","公众号订阅","小程序使用","添加好友","朋友圈点赞","红包发送","朋友圈评论"]}]

Example 3 (Generation for Unknown):
Query: Recommend a fitness app
Output: [{"app_name": "Keep", "description": "A fitness tracking and workout app", "icon_description": "Orange figure in motion with a checkmark", "common_functions": ["Track workouts", "Set fitness goals", "Join challenges", "Custom exercise plans", "Progress tracking", "Community sharing", "Video tutorials"]}]
"""

    prompt = (
        f"You are an app information generator. Based on the query, generate a list of apps with: app_name, description (brief intro), icon_description (visual description), common_functions (list of 5-10 key functions). Use general knowledge or similar apps to create new entries. This output will be used to build or extend app data JSON files. Keep output as a JSON array of objects. {lang_instruction}\n\n"
        + few_shot + "\n\n"
        "User Query: " + user_query + "\n\n"
        "Output: JSON array like [{'app_name': '...', 'description': '...', 'icon_description': '...', 'common_functions': ['...']}]"
    )
    return prompt

def call_gemini(prompt: str) -> tuple[str, dict]:
    """Call Gemini API and return text + usage."""
    api_key = os.getenv("GEMINI_API_KEY") or "sk-BAO0wS03Fb1KzKKXrGbbaHBGqolfc0jiKXqJAbljdXVyLDuy"
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set. Please set it in environment variables.")

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
        raise RuntimeError(f"Gemini API request failed: {e}")
    except (KeyError, IndexError):
        raise ValueError("Invalid Gemini API response format")

def generate_app_data(user_query: str, output_file: str = "app-ins.json") -> dict:
    """Main function: Generate app data based on query and append to output_file in array format."""
    start_time = time.time()
    prompt = build_prompt(user_query)

    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for attempt in range(3):
        response, usage = call_gemini(prompt)
        for key in total_usage:
            total_usage[key] += usage.get(key, 0)

        response = response.strip().strip('```json').strip('```').strip()

        try:
            parsed = json_repair.loads(response)
            if isinstance(parsed, list) and all(isinstance(item, dict) and 'app_name' in item for item in parsed):
                duration = time.time() - start_time
                result = {
                    "query": user_query,
                    "generated_apps": parsed,
                    "token_usage": total_usage,
                    "duration_seconds": duration,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                # Append to output_file in array format, similar to output.json
                history = []
                if os.path.exists(output_file):
                    with open(output_file, 'r', encoding='utf-8') as f:
                        history = json.load(f)
                        if not isinstance(history, list):
                            history = [history]
                    # Add id if missing in history
                    for i, item in enumerate(history):
                        if 'id' not in item:
                            item['id'] = i + 1
                # Add id and timestamp to new result
                result['id'] = len(history) + 1
                history.append(result)
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(history, f, indent=4, ensure_ascii=False)
                logging.info(f"Result appended to {output_file}")
                return result
        except Exception as e:
            logging.debug(f"Parse failed (attempt {attempt+1}): {str(e)}\nRaw response: {response}")

    duration = time.time() - start_time
    return {"error": "All retries failed", "duration_seconds": duration, "token_usage": total_usage}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_app_prep.py \"Your query\"")
        sys.exit(1)
    query = sys.argv[1]
    try:
        result = generate_app_data(query)
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(json.dumps(result, indent=4, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")
