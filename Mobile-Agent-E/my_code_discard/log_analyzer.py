import json
import os
import sys
import math

def analyze_log(log_dir):
    steps_json_path = os.path.join(log_dir, 'steps.json')
    if not os.path.exists(steps_json_path):
        print(f"steps.json not found in {log_dir}")
        return []

    with open(steps_json_path, 'r') as f:
        steps = json.load(f)

    action_records = []
    for s in steps:
        if s.get('operation') == 'action':
            step_num = s['step']
            action_str = s.get('action_object_str', 'N/A')
            action_obj = s.get('action_object', {})

            # Find pre perception for this step
            pre_perception = next((p for p in steps if p['step'] == step_num and p['operation'] == 'perception'), None)

            tapped_icon = 'N/A'
            if pre_perception and 'name' in action_obj and action_obj['name'] == 'Tap':
                infos = pre_perception.get('perception_infos', [])
                args = action_obj.get('arguments', {})
                if 'x' in args and 'y' in args:
                    tap_x = int(args['x'])
                    tap_y = int(args['y'])
                    if infos:
                        # Find closest
                        closest = min(infos, key=lambda info: math.sqrt((info['coordinates'][0] - tap_x)**2 + (info['coordinates'][1] - tap_y)**2))
                        dist = math.sqrt((closest['coordinates'][0] - tap_x)**2 + (closest['coordinates'][1] - tap_y)**2)
                        if dist < 50:  # threshold in pixels
                            tapped_icon = closest['text']
                        else:
                            tapped_icon = 'none_text'

            action_records.append({
                'step': step_num,
                'action_object_str': action_str,
                'tapped_icon': tapped_icon if tapped_icon != 'N/A' else ''
            })

    return action_records

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python log_analyzer.py <log_dir>")
        sys.exit(1)

    log_dir = sys.argv[1]
    records = analyze_log(log_dir)

    print("Action Records:")
    for rec in records:
        line = f"Step {rec['step']}: {rec['action_object_str']}"
        if rec['tapped_icon']:
            line += f" (Tapped: {rec['tapped_icon']})"
        print(line)
