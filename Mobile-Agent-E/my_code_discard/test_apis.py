import requests
import json

def test_third_party_api_key(api_key: str, url: str = "https://yunwu.ai/v1/chat/completions") -> bool:
    """
    测试第三方平台的 API Key 是否有效（兼容 OpenAI 风格）。
    通过发送一个简单的聊天完成请求来验证。
    
    :param api_key: API Key
    :param url: 第三方平台的端点 URL
    :return: True 如果有效，否则 False
    """
    try:
        # 构建完整的 URL（如果需要附加 key，根据平台调整；对于 OpenAI 风格，通常在 headers 中）
        full_url = url  # 如果平台要求 ?key={api_key}，则改为 f"{url}?key={api_key}"
        
        # 请求头（使用 Bearer 对于大多数 OpenAI 兼容平台）
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 请求体：OpenAI 兼容格式
        payload = {
            "model": "gpt-3.5-turbo",  # 替换为平台的实际模型名，例如 "moonshot-v1-8k" 或 "deepseek-chat"
            "messages": [
                {"role": "user", "content": "Hello, this is a test."}
            ],
            "max_tokens": 10
        }
        
        # 发送 POST 请求
        response = requests.post(full_url, headers=headers, data=json.dumps(payload))
        
        # 调试打印：响应状态和原始文本
        print(f"调试: 响应状态码: {response.status_code}")
        print(f"调试: 原始响应文本: {response.text[:200]}")  # 打印前 200 字符以避免过长
        
        # 检查响应状态码
        if response.status_code == 200:
            try:
                data = response.json()
                if "choices" in data and data["choices"]:
                    print("API Key 有效！测试响应:", data["choices"][0]["message"]["content"])
                    return True
                else:
                    print("响应成功但内容为空。原始响应:", response.text)
                    return False
            except json.JSONDecodeError as json_err:
                print(f"JSON 解析失败: {str(json_err)}。原始响应: {response.text}")
                return False
        else:
            print(f"API Key 无效或请求失败。状态码: {response.status_code}, 错误: {response.text}")
            return False
    
    except Exception as e:
        print(f"测试失败: {str(e)}")
        return False

# 使用示例
if __name__ == "__main__":
    # 在此处直接填写您的 Gemini API Key 和 URL
    api_key = "sk-67zxuDmeheoI5aMA3Vp1eHbTeiCD5enBo2HQLJIDvGDHanIK"  # 替换为您的实际 API Key
    test_url = "https://yunwu.ai/v1/chat/completions"  # 可自定义 URL
    test_third_party_api_key(api_key, test_url)
