import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from agent_tools import check_match_score, extract_job_keywords, write_cover_letter

load_dotenv()

llm = ChatOpenAI(
    model="deepseek-ai/DeepSeek-V4-Flash",
    api_key=os.getenv("SILICONFLOW_API_KEY"),
    base_url="https://api.siliconflow.cn/v1",
    temperature=0
)

tools = [check_match_score, extract_job_keywords, write_cover_letter]

SYSTEM_PROMPT = """You are a job application assistant that helps users decide whether a job posting
is worth applying to, and prepares application materials when appropriate.

Workflow:
1. When the user mentions a job, first call check_match_score to check the fit score.
2. If the score is below 0.5, tell the user directly that this job is not recommended.
   Do not call any further tools (avoid unnecessary API usage).
3. If the score is >= 0.5, you may call extract_job_keywords to review the requirements,
   and/or call write_cover_letter to generate a tailored cover letter.
4. At each step, explain to the user why you called a given tool and what you found.
"""

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=SYSTEM_PROMPT,
)


if __name__ == "__main__":
    # Sample run: full pipeline from match check to cover letter generation
    test_input = """
    I found this job and want to know if it's worth applying to.
    If so, please prepare a cover letter:
    Company: Shift Technology
    Link: https://www.adzuna.fr/details/5681609308?utm_medium=api&utm_source=373870c8
    """

    result = agent.invoke({
        "messages": [{"role": "user", "content": test_input}]
    })

    print("\n=== Full message chain (including each tool call) ===")
    for msg in result["messages"]:
        preview = msg.content[:300] if msg.content else "(tool call, no text content)"
        print(f"\n[{msg.type}] {preview}")

    print("\n\n=== Final response ===")
    print(result["messages"][-1].content)