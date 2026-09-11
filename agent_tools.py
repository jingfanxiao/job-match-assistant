import os
from dotenv import load_dotenv
from langchain.tools import tool
from resume_parser import parse_resume
from resume_chunker import chunk_resume
from matcher import calculate_match
from keyword_extractor import extract_keywords
from cover_letter_generator import retrieve_relevant_sections, generate_cover_letter
from jd_fetcher import fetch_jd_from_url

load_dotenv()

RESUME_PATH = os.getenv("RESUME_PATH", "resume.pdf")

# Preload resume once so tools don't re-parse the PDF on every call
_resume_text = parse_resume(RESUME_PATH)
_resume_chunks = chunk_resume(_resume_text)
_applicant_name = _resume_chunks["HEADER"].split("\n")[0].strip()


@tool
def check_match_score(job_url: str) -> str:
    """
    Fetch a job posting's JD from its URL and compute its match score (0-1)
    against the user's resume. Should be called first, before any other tool.
    """
    full_jd, error = fetch_jd_from_url(job_url)
    if error:
        return f"Could not fetch this job's JD: {error}"

    score = calculate_match(_resume_text, full_jd)
    return f"Match score: {score:.3f} (out of 1.0). JD content is cached for keyword extraction and cover letter generation."


@tool
def extract_job_keywords(job_url: str) -> str:
    """
    Extract structured requirements (hard skills, tools, experience) from a job
    posting's JD. Usually called after match score is confirmed to be good enough.
    """
    full_jd, error = fetch_jd_from_url(job_url)
    if error:
        return f"Could not fetch this job's JD: {error}"

    keywords = extract_keywords(full_jd)
    if keywords is None:
        return "Keyword extraction failed, JD content may be malformed"

    return f"Extracted keywords: {keywords}"


@tool
def write_cover_letter(job_url: str, company_name: str) -> str:
    """
    Generate a tailored cover letter for a job posting. Retrieves the most
    relevant resume sections, extracts JD keywords, and writes an English
    cover letter. Should only be called once match score is already confirmed.
    """
    full_jd, error = fetch_jd_from_url(job_url)
    if error:
        return f"Could not fetch this job's JD: {error}"

    keywords = extract_keywords(full_jd)
    if keywords is None:
        return "Keyword extraction failed, cannot generate cover letter"

    relevant_sections = retrieve_relevant_sections(keywords, _resume_chunks)
    letter = generate_cover_letter(
        full_jd, keywords, relevant_sections,
        applicant_name=_applicant_name,
        company_name=company_name
    )
    return f"Generated cover letter:\n\n{letter}"


if __name__ == "__main__":
    # Sanity check: call each tool directly, bypassing the agent
    test_url = "https://www.adzuna.fr/details/5681609308?utm_medium=api&utm_source=373870c8"

    print("=== Testing check_match_score ===")
    print(check_match_score.invoke({"job_url": test_url}))