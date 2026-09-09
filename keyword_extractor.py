from openai import OpenAI
import json
import os
from dotenv import load_dotenv
load_dotenv()
client = OpenAI(
    api_key=os.getenv("SILICONFLOW_API_KEY"),
    base_url="https://api.siliconflow.cn/v1"
)

def extract_keywords(jd_text):
    prompt = f"""你是一个招聘JD分析专家。请从以下岗位描述中提取核心要求,严格按照JSON格式输出,不要有任何多余的文字或markdown标记。

JD内容:
{jd_text[:3000]}

请输出以下JSON结构:
{{
    "hard_skills": ["skill 1", "skill 2", ...],
    "soft_skills": ["skill 1", "skill2", ...],
    "tools_languages": ["1", "2", ...],
    "experience_requirements": ["1", "", ...],
    "education_requirements": "description of the education"
}}
"""
    
    response = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V4-Flash",
        messages=[{"role": "user", "content": prompt}],
        extra_body={"thinking": {"type": "disabled"}}
    )
    
    raw_output = response.choices[0].message.content.strip()
    
    # 防御性处理:去掉可能的markdown代码块标记
    if raw_output.startswith("```"):
        raw_output = raw_output.split("```")[1]
        if raw_output.startswith("json"):
            raw_output = raw_output[4:]
    
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError as e:
        print(f"JSON analyse failed: {e}")
        print(f"origin output: {raw_output}")
        return None

if __name__ == "__main__":
    from jd_fetcher import fetch_jd_from_url
    
    url = "https://www.adzuna.fr/details/5681609308?utm_medium=api&utm_source=373870c8"
    jd_text, error = fetch_jd_from_url(url)
    
    if error:
        print(error)
    else:
        keywords = extract_keywords(jd_text)
        print(json.dumps(keywords, indent=2, ensure_ascii=False))