import os
from dotenv import load_dotenv
from openai import OpenAI

# 1. 从 .env 读入 DEEPSEEK_API_KEY
load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise SystemExit("没有读到 DEEPSEEK_API_KEY，请检查 .env 文件")

# 2. 创建 client，指向 DeepSeek
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)

# 3. 发一条消息给大模型
resp = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "user", "content": "用一句话解释什么是 AI Agent"}
    ],
)

# 4. 打印回答
print(resp.choices[0].message.content)