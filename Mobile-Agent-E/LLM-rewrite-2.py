# LLM-rewrite.py: 使用 Gemini-1.5-pro 模型补充用户指令，基于模型的通用能力
# 参考 instruction_rewrite.py 的结构，但不注入任何外部 JSON 数据，且无 few-shot 示例

import json
import os
import requests
import re
import logging
import json_repair
import unicodedata
import datetime
import time

logging.basicConfig(level=logging.DEBUG)

GEMINI_MODEL = "gemini-2.5-pro"
API_ENDPOINT = "https://yunwu.ai/v1/chat/completions"

def detect_language(text: str) -> str:
    for char in text:
        if unicodedata.category(char).startswith('Lo') and 'CJK' in unicodedata.name(char, ''):
            return 'zh'
    return 'en'

def build_prompt(user_instruction: str) -> str:
    lang = detect_language(user_instruction)
    lang_instruction = "Output in English if the user input is in English, or in Chinese if in Chinese." if lang == 'en' else "如果用户输入是中文，则输出中文；如果是英文，则输出英文。"

    prompt = (
        f"You are an instruction rewriting assistant. Based on your general knowledge, rewrite the user instruction into level 2 (summary of operations) and level 3 (detailed step-by-step path). Decide on appropriate apps and paths yourself without specific examples. Keep output concise. {lang_instruction}\n\n"
        "用户指令：" + user_instruction + "\n\n"
        "输出：JSON格式，包括{'level2_instruction': '2级指令', 'level3_instruction': '3级指令', 'reason': '简要理由'}"
    )
    return prompt

def call_gemini(prompt: str) -> tuple[str, dict]:
    api_key = os.getenv("GEMINI_API_KEY") or "sk-BAO0wS03Fb1KzKKXrGbbaHBGqolfc0jiKXqJAbljdXVyLDuy"
    if not api_key:
        raise ValueError("GEMINI_API_KEY 未设置")

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
    user_input =  "Book an off-season flight to Reykjavik, Iceland." 
    try:
        for i in range(2):
            result = rewrite_instruction(user_input, save_to_file="LLM-output.json")
            if "error" in result:
                print(f"Run {i+1} 错误: {result['error']}")
            else:
                print(f"Run {i+1} 原指令:", result["original_instruction"])
                print(f"Run {i+1} 补充后的2级指令:", result["level2_instruction"])
                print(f"Run {i+1} 最终的补充指令:", result["level3_instruction"])
                print(f"Run {i+1} 理由:", result["reason"])
                print(f"Run {i+1} Token Usage:", result["token_usage"])
                print(f"Run {i+1} Duration: {result['duration_seconds']} seconds")
    except Exception as e:
        print(f"错误: {e}")
