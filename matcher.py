import os
from dotenv import load_dotenv
from openai import OpenAI
import numpy as np

load_dotenv()

RESUME_PATH = os.getenv("RESUME_PATH", "resume.pdf")

client = OpenAI(
    api_key=os.getenv("SILICONFLOW_API_KEY"),
    base_url="https://api.siliconflow.cn/v1"
)


def get_embedding(text):
    response = client.embeddings.create(
        model="BAAI/bge-m3",
        input=text
    )
    return np.array(response.data[0].embedding)


def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


def calculate_match(resume_text, jd_text):
    resume_vec = get_embedding(resume_text)
    jd_vec = get_embedding(jd_text)
    return cosine_similarity(resume_vec, jd_vec)


if __name__ == "__main__":
    from resume_parser import parse_resume

    resume_text = parse_resume(RESUME_PATH)

    # One relevant and one irrelevant JD, used to sanity-check that scores
    # actually differ in the expected direction
    jd_relevant = """
    Data Science Intern - 6 months
    We are looking for a Master's student specializing in Data & AI
    to join our team starting November 2026. You will work on machine
    learning models, data pipelines, and analytics projects.
    """

    jd_irrelevant = """
    Marketing Manager Position
    We need an experienced marketing professional to lead our brand
    campaigns, manage social media strategy, and coordinate with
    external agencies for advertising.
    """

    score_relevant = calculate_match(resume_text, jd_relevant)
    score_irrelevant = calculate_match(resume_text, jd_irrelevant)

    print(f"Relevant JD match score: {score_relevant:.3f}")
    print(f"Irrelevant JD match score: {score_irrelevant:.3f}")