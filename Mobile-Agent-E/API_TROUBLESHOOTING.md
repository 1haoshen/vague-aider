# OpenRouter API 401错误解决方案

## 问题诊断

如果你遇到 `401 Client Error: Unauthorized` 错误，说明API认证失败。

## 可能原因及解决方案

### 1. API Key问题
**症状**: 所有请求都返回401错误

**解决方案**:
```bash
# Windows PowerShell
$env:OPENROUTER_API_KEY = "your_actual_api_key_here"

# Windows CMD
set OPENROUTER_API_KEY=your_actual_api_key_here

# 永久设置（Windows）
# 环境变量 -> 系统变量 -> 新建 OPENROUTER_API_KEY
```

### 2. 模型名称不存在
**症状**: models端点工作但chat completions返回404

**解决方案**: 使用以下可用模型之一：
- `google/gemini-pro-1.5` (推荐)
- `google/gemini-pro`
- `google/gemini-flash-1.5`
- `anthropic/claude-3-haiku` (备选)
- `openai/gpt-4o-mini` (备选)

### 3. 账户余额不足
**症状**: 某些请求返回402错误

**解决方案**: 访问 [OpenRouter](https://openrouter.ai/) 充值账户

### 4. 账户权限问题
**症状**: API Key有效但某些模型不可访问

**解决方案**: 检查OpenRouter账户的权限设置

## 快速修复步骤

1. **获取新的API Key**:
   - 访问 https://openrouter.ai/
   - 注册/登录账户
   - 生成新的API Key

2. **设置环境变量**:
   ```bash
   # 设置环境变量（替换为你的真实API Key）
   set OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxx
   ```

3. **修改代码** (可选):
   ```python
   # 在脚本开头修改模型名称
   GEMINI_MODEL = "google/gemini-pro-1.5"  # 或其他可用模型
   ```

4. **测试连接**:
   ```bash
   python simple_test.py
   ```

## 备用方案

如果OpenRouter持续有问题，可以考虑：

1. **使用Google Gemini直接API**:
   ```python
   # 替换为Google Gemini API
   API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
   GEMINI_MODEL = "gemini-pro"
   ```

2. **使用其他API提供商**:
   - OpenAI API
   - Anthropic Claude API
   - 本地部署模型

## 验证步骤

运行以下Python代码验证API连接：

```python
import requests

api_key = "your_api_key_here"
headers = {'Authorization': f'Bearer {api_key}'}

# 测试账户
resp = requests.get('https://openrouter.ai/api/v1/auth/key', headers=headers)
print(f"账户状态: {resp.status_code}")

# 测试模型列表
resp = requests.get('https://openrouter.ai/api/v1/models', headers=headers)
print(f"模型列表: {resp.status_code}")

# 测试chat completion
payload = {
    "model": "google/gemini-pro-1.5",
    "messages": [{"role": "user", "content": "Hello"}]
}
resp = requests.post('https://openrouter.ai/api/v1/chat/completions',
                    json=payload, headers=headers)
print(f"Chat completion: {resp.status_code}")
```

## 常见错误代码

- `401`: API Key无效
- `402`: 余额不足
- `404`: 模型不存在
- `429`: 请求频率过高
- `500`: 服务器错误







