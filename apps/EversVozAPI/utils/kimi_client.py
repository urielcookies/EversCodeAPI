import os
from openai import OpenAI

kimi_client = OpenAI(
    base_url="https://api.moonshot.cn/v1",
    api_key=os.getenv("KIMI_API_KEY")
)
