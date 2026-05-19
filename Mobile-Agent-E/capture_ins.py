# capture_ins.py: Extract features from steps.json in Mobile-Agent-E logs

import json
import os
import re
from typing import List, Dict
import argparse  # Ensure at top

def extract_features(steps_file: str, output_file: str) -> None:
    """
    Extract specified features from a steps.json file and save to output JSON.
    
    :param steps_file: Path to the input steps.json file.
    :param output_file: Path to the output JSON file.
    """
    try:
        if not os.path.exists(steps_file):
            raise FileNotFoundError(f"File not found: {steps_file}")
        
        with open(steps_file, 'r', encoding='utf-8') as f:
            steps = json.load(f)
    except FileNotFoundError as e:
        print(f"Error: {e}. Verify the path and ensure steps.json exists.")
        return
    except json.JSONDecodeError:
        print("Error: Invalid JSON in file. Check steps.json.")
        return
    except Exception as e:
        print(f"Unexpected error: {e}")
        return
    
    extracted_data = []
    total_prompt_tokens = 0
    total_raw_response_tokens = 0
    
    for step in steps:
        if step.get('operation') == 'perception':
            continue  # Skip perception steps as in deal_log.py
        
        # Extract features
        action_object_str = step.get('action_object_str', '')
        # Replace coordinates with text descriptions
        action_object_str = replace_coordinates(action_object_str, step)
        
        action_description = step.get('action_description', '')
        action_thought = step.get('action_thought', '')
        current_subgoal = step.get('current_subgoal', '')
        duration = step.get('duration', 0)
        
        # Accumulate tokens
        prompt = ''.join(str(step.get(k, '')) for k in step if k.startswith('prompt_'))
        raw_response = str(step.get('raw_response', ''))
        total_prompt_tokens += len(prompt.split())
        total_raw_response_tokens += len(raw_response.split())
        
        # Skip if all four fields are empty
        if (action_object_str == '' and 
            action_description == '' and 
            action_thought == '' and 
            current_subgoal == ''):
            continue  # Still accumulate tokens, but skip saving this step
        
        extracted_data.append({
            'step': step.get('step', -1),
            'action_object_str': action_object_str,
            'action_description': action_description,
            'action_thought': action_thought,
            'current_subgoal': current_subgoal,
            'duration': duration
        })
    
    # Always add totals
    extracted_data.append({
        'totals': {
            'prompt_tokens': total_prompt_tokens,
            'raw_response_tokens': total_raw_response_tokens
        }
    })
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, ensure_ascii=False, indent=4)
        print(f"Saved to {output_file}")
    except Exception as e:
        print(f"Save error: {e}")

def replace_coordinates(action_str: str, step: Dict) -> str:
    """
    Replace coordinates in action_object_str with text descriptions.
    Use perception_infos or other context from the step.
    """
    # Simple regex to find coordinates like (x, y)
    coord_pattern = r'\(\d+,\s*\d+\)'
    matches = re.findall(coord_pattern, action_str)
    
    # For demonstration, replace with placeholder descriptions
    # In real implementation, map to actual objects from perception_infos
    perception_infos = step.get('perception_infos', [])
    for match in matches:
        # Placeholder: assume first match is 'icon', etc.
        description = 'icon'  # Replace with actual logic
        action_str = action_str.replace(match, description)
    
    return action_str

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("log_dir", type=str, help="Log directory with steps.json")
    
    args = parser.parse_args()
    
    input_path = os.path.join(args.log_dir, "steps.json")
    output_path = os.path.join(args.log_dir, "path-ins.json")
    
    extract_features(input_path, output_path)
