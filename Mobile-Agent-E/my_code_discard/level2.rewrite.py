# instruction_rewrite.py: 使用 Gemini-2.5-pro 模型补充用户指令，基于 app-data-2.json
# 参考 Mobile-Agent-E 项目（如 api.py 中的 API 调用和 Prompt 构建）
# 原因：实现查询功能，提供可运行脚本，便于扩展
#最初的1级改写为2级的脚本 备份

import json
import os
import requests
import re  # 新增：用于关键词提取
import logging  # 新增：用于日志

logging.basicConfig(level=logging.DEBUG)  # 设置日志级别

# 默认路径（参考项目布局，可自定义）
APP_DATA_PATH = "../app-data/app-data-2.json"
GEMINI_MODEL = "gemini-2.5-pro"  # 指定模型
API_ENDPOINT = f"https://yunwu.ai/v1/chat/completions"

def load_app_data(file_path: str = APP_DATA_PATH) -> dict:
    """读取 app-data-2.json 文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"app-data-2.json 未找到于 {file_path}")
    except json.JSONDecodeError:
        raise ValueError("app-data-2.json 格式无效")

def build_prompt(user_instruction: str, app_data: dict) -> str:
    """构建 Prompt，注入 app-data-2.json 内容（增强版：动态提取 + 过滤）"""
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
    app_data_str = json.dumps(filtered_apps or app_data, indent=2, ensure_ascii=False)

    # 增强few-shot：添加链式推理指导
    few_shot = """
示例1:
用户指令: 打开微信
app-data-2.json 数据: [{"appname": "微信", "description": "聊天app", "functions": ["发送消息"]}]
输出: {'rewritten_instruction': '打开微信app，进入聊天界面发送消息', 'referenced_apps': ['微信'], 'reason': '基于functions生成聊天步骤'}

示例2:
用户指令: 查找商品
app-data-2.json 数据: [{"appname": "淘宝", "description": "电商app", "functions": ["搜索商品"]}]
输出: {'rewritten_instruction': '打开淘宝app，点击搜索栏输入商品名称', 'referenced_apps': ['淘宝'], 'reason': '参考description和functions补充搜索细节'}

示例3 (边缘): 
用户指令: 处理未知app
app-data-2.json 数据: []  # 无匹配
输出: {'rewritten_instruction': '尝试打开默认app处理', 'referenced_apps': [], 'reason': '无匹配app，回退默认'}
"""

    prompt = (
        "你是一个指令补充助手，先从app-data-2.json匹配相关app（基于appname），然后参考description和functions生成步骤式指令。如果无匹配，使用通用逻辑。保持输出简洁，仅包含必要步骤。\n\n"  # 新增简洁指导
        + few_shot + "\n\n"
        "app-data-2.json 数据：\n" + app_data_str + "\n\n"
        "用户指令：" + user_instruction + "\n\n"
        "输出：JSON格式，包括{'rewritten_instruction': '补充后的指令', 'referenced_apps': ['引用的appname'], 'reason': '简要理由'}"
    )
    return prompt

def call_gemini(prompt: str) -> str:
    """调用 Gemini API（修改为 OpenAI 兼容格式，参考 test_gemini.py）"""
    api_key = os.getenv("GEMINI_API_KEY") or "sk-BAO0wS03Fb1KzKKXrGbbaHBGqolfc0jiKXqJAbljdXVyLDuy"  # 从环境变量获取，或使用默认（测试用）
    if not api_key:
        raise ValueError("GEMINI_API_KEY 未设置，请在环境变量中设置")

    payload = {
        "model": GEMINI_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1024,  # 增加到1024以避免截断
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
        # 提取生成的文本（OpenAI 兼容响应结构）
        generated_text = result["choices"][0]["message"]["content"]
        return generated_text
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Gemini API 请求失败: {e}")
    except (KeyError, IndexError):
        raise ValueError("Gemini API 响应格式无效")

# 更新解析以匹配新输出结构
def rewrite_instruction(user_instruction: str) -> str:
    """主函数：补充用户指令"""
    app_data = load_app_data()
    prompt = build_prompt(user_instruction, app_data)
    
    for attempt in range(3):  # 新增：重试机制，最多3次
        response = call_gemini(prompt)
        
        # 新增：清理markdown/code blocks
        response = response.strip().strip('```json').strip('```').strip()
        
        try:
            parsed = json.loads(response)
            if 'rewritten_instruction' not in parsed:  # 新增：检查完整性
                return "响应不完整: " + response
            return f"改写指令: {parsed['rewritten_instruction']}\n引用app: {parsed['referenced_apps']}\n理由: {parsed['reason']}"
        except (json.JSONDecodeError, KeyError) as e:
            logging.debug(f"解析失败 (尝试 {attempt+1}): {str(e)}\n原始响应: {response}")  # 增强日志
            if attempt == 2:
                return "解析失败（可能截断，已重试）： " + response  # 最终错误消息

# 示例使用
if __name__ == "__main__":
    user_input = "给我推荐几个广州的景点"  # 示例用户指令
    try:
        result = rewrite_instruction(user_input)
        print("原指令:", user_input)
        print("补充后的指令:", result)
    except Exception as e:
        print(f"错误: {e}")
