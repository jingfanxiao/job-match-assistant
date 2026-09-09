from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(
    api_key=os.getenv("SILICONFLOW_API_KEY"),
    base_url="https://api.siliconflow.cn/v1"
)

response = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-V4-Flash",
    messages=[{"role": "user", "content": "hello, say one phrase to prove that you're online"}],
    extra_body={"thinking": {"type": "disabled"}}  # 关闭思考模式,加快速度、省token
)

print(response.choices[0].message.content)