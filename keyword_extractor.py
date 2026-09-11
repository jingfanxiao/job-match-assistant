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
    """Extract structured requirements from a JD into a fixed JSON schema."""
    prompt = f"""You are a recruitment JD analysis expert. Extract the core requirements from the job description below.
Output strictly as JSON, with no extra text or markdown formatting.

JD content:
{jd_text[:3000]}

Output this exact JSON structure:
{{
    "hard_skills": ["skill 1", "skill 2", ...],
    "soft_skills": ["skill 1", "skill 2", ...],
    "tools_languages": ["tool 1", "tool 2", ...],
    "experience_requirements": ["requirement 1", "requirement 2", ...],
    "education_requirements": "description of the education requirement"
}}
"""

    response = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V4-Flash",
        messages=[{"role": "user", "content": prompt}],
        extra_body={"thinking": {"type": "disabled"}}
    )

    raw_output = response.choices[0].message.content.strip()

    # Defensive cleanup: some models wrap JSON in a markdown code block anyway
    if raw_output.startswith("```"):
        raw_output = raw_output.split("```")[1]
        if raw_output.startswith("json"):
            raw_output = raw_output[4:]

    try:
        return json.loads(raw_output)
    except json.JSONDecodeError as e:
        print(f"JSON parse failed: {e}")
        print(f"Raw output: {raw_output}")
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