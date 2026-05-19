# get_app.py: Prompt Search Tool for Generating App List Information

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

# Default paths and model
APP_DATA_PATH = "cn-en-app-data-action-str.json"
GEMINI_MODEL = "gemini-2.5-pro"
API_ENDPOINT = "https://yunwu.ai/v1/chat/completions"

def load_app_data(file_path: str = APP_DATA_PATH) -> list:
    """Load app data from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("App data must be a list of dictionaries.")
            return data
    except FileNotFoundError:
        raise FileNotFoundError(f"App data file not found at {file_path}")
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in app data file")

def detect_language(text: str) -> str:
    """Detect language: 'zh' if Chinese characters are present, else 'en'."""
    for char in text:
        if unicodedata.category(char).startswith('Lo') and 'CJK' in unicodedata.name(char, ''):
            return 'zh'
    return 'en'

def build_prompt(user_query: str, app_data: list) -> str:
    """Build prompt injecting filtered app data as Few-Shot examples."""
    lang = detect_language(user_query)
    lang_instruction = "Output in English if the query is in English, or in Chinese if in Chinese." if lang == 'en' else "如果查询是中文，则输出中文；如果是英文，则输出英文。"

    # Extract keywords from query
    keywords = re.findall(r'\w+', user_query.lower())

    # Filter relevant apps (top 5 to limit length)
    filtered_apps = [
        {'appname': app.get('appname'), 'description': app.get('description'), 'functions': app.get('functions')}
        for app in app_data
        if isinstance(app, dict) and any(kw in app.get('appname', '').lower() for kw in keywords)
    ][:5]
    app_data_str = json.dumps(filtered_apps or app_data[:5], indent=2, ensure_ascii=False)  # Use first 5 if no match

    # Few-Shot examples based on typical app data structure
    few_shot = """
Example 1 (English Query):
Query: Recommend a chat app
App Data Sample: [{"appname": "WeChat", "description": "A messaging and calling app", "functions": ["Send message", "Voice call"]}]
Output: [{"app_name": "WeChat", "description": "A messaging and calling app for communication", "icon_description": "Green speech bubble with two white chat icons", "common_functions": ["Send text messages", "Make voice calls", "Share moments"]}]

Example 2 (Chinese Query):
Query: 推荐一个聊天app
App Data Sample: [{"appname": "微信", "description": "聊天和通话app", "functions": ["发送消息", "语音通话"]}]
Output: [{"app_name": "微信", "description": "用于通信的聊天和通话app", "icon_description": "绿色气泡图标带有两个白色聊天符号", "common_functions": ["发送文本消息", "进行语音通话", "分享朋友圈"]}]

Example 3 (No Match):
Query: Unknown app type
App Data Sample: []
Output: [{"app_name": "Generic App", "description": "A placeholder app", "icon_description": "Blue circle icon", "common_functions": ["Basic operations"]}]
"""

    prompt = (
        f"You are an app information generator. Based on the query, search or generate a list of apps from the provided app data sample. For each app, provide: app_name, description (brief intro), icon_description (visual description), common_functions (list of 3-5 key functions). If no direct match, generate based on similar apps or general knowledge. Keep output as a JSON array of objects. {lang_instruction}\n\n"
        + few_shot + "\n\n"
        "App Data Sample:\n" + app_data_str + "\n\n"
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

def get_app_list(user_query: str, output_file: str = "app_list.json") -> dict:
    """Main function: Generate app list based on query."""
    start_time = time.time()
    app_data = load_app_data()
    prompt = build_prompt(user_query, app_data)

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
                    "app_list": parsed,
                    "token_usage": total_usage,
                    "duration_seconds": duration,
                    "timestamp": datetime.datetime.now().isoformat()
                }
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=4, ensure_ascii=False)
                logging.info(f"Output saved to {output_file}")
                return result
        except Exception as e:
            logging.debug(f"Parse failed (attempt {attempt+1}): {str(e)}\nRaw response: {response}")

    duration = time.time() - start_time
    return {"error": "All retries failed", "duration_seconds": duration, "token_usage": total_usage}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_app.py \"Your query\"")
        sys.exit(1)
    query = sys.argv[1]
    try:
        result = get_app_list(query)
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(json.dumps(result, indent=4, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")
