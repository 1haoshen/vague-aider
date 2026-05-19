# path-get.py: Updated to generate action trajectories from path-ins.json sequence

import json
import os
import requests  # For API calls
import argparse  # Add at the top after imports

# Gemini API settings (adapt from instruction_rewrite.py)
GEMINI_MODEL = "gemini-2.5-pro"
API_ENDPOINT = "https://yunwu.ai/v1/chat/completions"
API_KEY = "sk-BAO0wS03Fb1KzKKXrGbbaHBGqolfc0jiKXqJAbljdXVyLDuy"  # Replace with actual key

def call_gemini(prompt: str) -> str:
    """Call Gemini API to generate description."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    payload = {
        "model": GEMINI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,  # Increased
        "temperature": 0.0
    }
    try:
        response = requests.post(API_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"API error: {e}")
        return ""

def process_path_ins(input_file: str, output_file: str) -> None:
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract steps (exclude totals)
    steps = [item for item in data if 'totals' not in item]
    
    # Concatenate fields for prompt
    sequence_summary = ""
    for item in steps:
        sequence_summary += f"Step {item.get('step')}: Subgoal: {item.get('current_subgoal', '')}, Action Str: {item.get('action_object_str', '')}, Description: {item.get('action_description', '')}, Thought: {item.get('action_thought', '')}\n"
    
    # Few-shot examples (hardcoded from cn-en-app-data-action-str.json)
    few_shot = """
Example 1: For function "在 YouTube 上搜索视频":
["open youtube app", "tap search box at the right top", "type the search content", "tap the first search result in the result list", "swipe down to cross out ads and see more results", "tap a video in the search result to enter the video page"]

Example 2: For function "获取到目的地的导航路线":
["open google maps app", "tap search box at the top", "type the destination", "tap the first search result in the result list", "tap the Directions button in a green box", "type the start location", "tap the first search result in the result list", "tap the preview button in a dark green box at the bottom"]

Example 3: For function "与朋友分享视频" (Share video with friends):
["open youtube app", "tap search box at the right top", "type the search content", "tap the first search result in the result list", "swipe down to cross out ads and see more results", "tap a video in the search result to enter the video page", "tap the right-pointing arrow with text 'share' in the right column", "tap a social software to share the video to friends"]
"""
    
    # Build prompt
    prompt = f"""
Based on the following sequence of steps from a task execution, infer and generate a series of action trajectories. Each trajectory should be an array of step-by-step actions, similar to action_object_str in app-data JSON.

Few-shot examples:
{few_shot}

Sequence of steps:
{sequence_summary}

Analyze the sequence to identify distinct functions or paths (e.g., search, add to playlist, share). For each, output an array of actions.

If sharing is detected, include a dedicated sharing path.

Output ONLY a valid JSON object: {{"generated_paths": [ [action1, action2, ...], [path2_action1, ...] ] }}
"""
    
    generated = call_gemini(prompt)
    print("Model generated:", generated)  # Debug
    
    try:
        output_data = json.loads(generated)
        if not isinstance(output_data.get('generated_paths'), list):
            raise ValueError("Invalid format")
    except (json.JSONDecodeError, ValueError):
        output_data = {"generated_paths": [], "error": "Failed to generate paths"}  # Fallback
    
    # Add original totals if present
    totals = next((item for item in data if 'totals' in item), {})
    if totals:
        output_data['totals'] = totals['totals']
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process path-ins.json")
    parser.add_argument("log_dir", type=str, help="Directory containing path-ins.json")
    
    args = parser.parse_args()
    
    input_path = os.path.join(args.log_dir, "path-ins.json")
    output_path = os.path.join(args.log_dir, "processed-path-ins.json")
    
    process_path_ins(input_path, output_path)
    print(f"Processed and saved to {output_path}")
