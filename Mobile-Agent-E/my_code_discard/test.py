import requests
import json

def test_gemini_api_key(api_key: str, url: str = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent") -> bool:
    """
    使用 requests 库测试 Gemini API Key 是否有效。
    通过发送一个简单的生成内容请求来验证。
    
    :param api_key: Gemini API Key
    :param url: Gemini API 的端点 URL（默认使用 gemini-1.5-flash 模型）
    :return: True 如果有效，否则 False
    """
    try:
        # 构建完整的 URL，附加 API Key
        full_url = f"{url}?key={api_key}"
        
        # 请求头
        headers = {
            "Content-Type": "application/json"
        }
        
        # 请求体：一个简单的测试提示
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": "Hello, this is a test."}
                    ]
                }
            ]
        }
        
        # 发送 POST 请求
        response = requests.post(full_url, headers=headers, data=json.dumps(payload))
        
        # 检查响应状态码
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and data["candidates"]:
                print("API Key 有效！测试响应:", data["candidates"][0]["content"]["parts"][0]["text"])
                return True
            else:
                print("响应成功但内容为空。")
                return False
        else:
            print(f"API Key 无效或请求失败。状态码: {response.status_code}, 错误: {response.text}")
            return False
    
    except Exception as e:
        print(f"测试失败: {str(e)}")
        return False

# 使用示例
if __name__ == "__main__":
    api_key = input("请输入您的 Gemini API Key: ")  # 或从环境变量获取
    test_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"  # 可自定义
    test_gemini_api_key(api_key, test_url)