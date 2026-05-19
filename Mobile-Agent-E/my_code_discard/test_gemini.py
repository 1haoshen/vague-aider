import requests
import json

def test_gemini_api_key(api_key: str, url: str = "https://yunwu.ai/v1/chat/completions") -> bool:
    """
    使用 requests 库测试 Gemini API Key 是否有效（使用用户提供的 URL）。
    注意: 此 URL 可能不是标准 Gemini 端点（标准为 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent'）。
    如果测试失败，请尝试标准 URL 并获取真实的 Gemini Key (从 Google AI Studio)。
    #https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
    :param api_key: Gemini API Key
    :param url: API 端点 URL
    :return: True 如果有效，否则 False
    """
    try:
        # 构建完整的 URL，附加 API Key (Gemini 风格)
        full_url = url  # 不使用 ?key= 参数
        
        # 请求头 (如果需要 Bearer，取消注释)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"  # 使用 Bearer Token
        }
        
        # 请求体：OpenAI 兼容格式 (因为 URL 有 /chat/completions)
        payload = {
            "model": "gemini-2.5-pro",  # 或 "gemini-2.5-pro" 如果可用
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
                if "choices" in data and data["choices"]:  # OpenAI 风格解析
                    print("API Key 有效！测试响应:", data["choices"][0]["message"]["content"])
                    return True
                elif "candidates" in data and data["candidates"]:  # Gemini 风格备用
                    print("API Key 有效！测试响应:", data["candidates"][0]["content"]["parts"][0]["text"])
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
    api_key = "sk-BAO0wS03Fb1KzKKXrGbbaHBGqolfc0jiKXqJAbljdXVyLDuy"  # 从 Google AI Studio 获取并替换
    test_url = "https://yunwu.ai/v1/chat/completions"  # 可自定义（如 gemini-1.5-flash）
    test_gemini_api_key(api_key, test_url)
