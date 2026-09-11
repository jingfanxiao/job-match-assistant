import os
from openai import OpenAI
from dotenv import load_dotenv
from matcher import get_embedding, cosine_similarity

load_dotenv()

client = OpenAI(
    api_key=os.getenv("SILICONFLOW_API_KEY"),
    base_url="https://api.siliconflow.cn/v1"
)


def retrieve_relevant_sections(keywords_dict, resume_chunks, top_k=3):
    """
    Retrieval step (the 'R' in mini-RAG): flatten JD keywords into one query
    string, then return the top_k resume sections most semantically similar to it.
    """
    query_terms = []
    for category, items in keywords_dict.items():
        if isinstance(items, list):
            query_terms.extend(items)
    query_text = " ".join(query_terms)

    query_vec = get_embedding(query_text)

    section_scores = []
    for section, content in resume_chunks.items():
        if section == "HEADER":  # contact info, not useful for generation
            continue
        section_vec = get_embedding(content)
        score = cosine_similarity(query_vec, section_vec)
        section_scores.append((section, content, score))

    section_scores.sort(key=lambda x: x[2], reverse=True)
    return section_scores[:top_k]


def generate_cover_letter(jd_text, keywords_dict, relevant_sections, applicant_name="", company_name="", tone="professional"):
    """Generation step: write a cover letter grounded in retrieved resume sections + JD keywords."""
    sections_text = "\n\n".join([
        f"[{section}]\n{content}" for section, content, score in relevant_sections
    ])

    hard_skills = keywords_dict.get("hard_skills", [])
    tools = keywords_dict.get("tools_languages", [])

    tone_instruction = {
        "professional": "formal and professional",
        "enthusiastic": "enthusiastic but still professional",
        "concise": "concise and direct, no filler"
    }.get(tone, "formal and professional")

    prompt = f"""You are a professional cover letter writing assistant. Write a tailored cover letter in ENGLISH based on the information below.

Applicant name: {applicant_name}
Target company: {company_name if company_name else "the company"}

Job's core required skills: {', '.join(hard_skills[:5])}
Job's required tools/languages: {', '.join(tools[:5])}

Applicant's most relevant resume excerpts (use ONLY these facts, do not invent experience):
{sections_text}

Requirements:
1. Write in English.
2. Tone: {tone_instruction}
3. Length: 250-350 words.
4. CRITICAL: Only reference experience that is explicitly present in the resume excerpts above.
   Do NOT invent or infer specific application domains, tools, or experience not mentioned.
   If the applicant has coursework but no hands-on project in a required skill, say so honestly
   (e.g. "currently building foundational knowledge through coursework in X") rather than implying
   direct experience.
5. Sign off with the applicant's real name: {applicant_name}. Do not use placeholder text like "[Your Name]".
6. Output only the cover letter body, no preamble or explanation.
"""

    response = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V4-Flash",
        messages=[{"role": "user", "content": prompt}],
        extra_body={"thinking": {"type": "disabled"}}
    )

    return response.choices[0].message.content.strip()


if __name__ == "__main__":
    from resume_parser import parse_resume
    from resume_chunker import chunk_resume
    from jd_fetcher import fetch_jd_from_url
    from keyword_extractor import extract_keywords

    RESUME_PATH = os.getenv("RESUME_PATH", "resume.pdf")

    resume_text = parse_resume(RESUME_PATH)
    resume_chunks = chunk_resume(resume_text)

    # First line of the resume is assumed to be the applicant's name
    applicant_name = resume_chunks["HEADER"].split("\n")[0].strip()
    print(f"Applicant name: {applicant_name}")

    url = "https://www.adzuna.fr/details/5681609308?utm_medium=api&utm_source=373870c8"
    jd_text, _ = fetch_jd_from_url(url)
    keywords = extract_keywords(jd_text)

    print("\n=== Retrieved relevant resume sections ===")
    relevant = retrieve_relevant_sections(keywords, resume_chunks)
    for section, content, score in relevant:
        print(f"[{score:.3f}] {section}: {content[:100]}...")

    print("\n=== Generated cover letter ===")
    letter = generate_cover_letter(
        jd_text,
        keywords,
        relevant,
        applicant_name=applicant_name,
        company_name="Shift Technology"
    )
    print(letter)