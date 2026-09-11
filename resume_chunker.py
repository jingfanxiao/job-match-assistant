import re
import os
from dotenv import load_dotenv

load_dotenv()

RESUME_PATH = os.getenv("RESUME_PATH", "resume.pdf")


def chunk_resume(resume_text):
    """
    Split resume text into sections by common header names.
    A rough, keyword-based split — not perfect, but works for most
    standard-format resumes.
    """
    section_headers = [
        "OBJECTIVE", "EDUCATION", "EXPERIENCE", "WORK EXPERIENCE",
        "PROJECTS", "SKILLS", "TECHNICAL SKILLS", "CERTIFICATIONS",
        "LANGUAGES", "INTERESTS", "EXTRACURRICULAR"
    ]

    pattern = "|".join([re.escape(h) for h in section_headers])
    splits = re.split(f"({pattern})", resume_text)

    chunks = {}
    current_section = "HEADER"  # name/contact info block
    buffer = ""

    for part in splits:
        part_stripped = part.strip()
        if part_stripped in section_headers:
            if buffer.strip():
                chunks[current_section] = buffer.strip()
            current_section = part_stripped
            buffer = ""
        else:
            buffer += part

    if buffer.strip():
        chunks[current_section] = buffer.strip()

    return chunks


if __name__ == "__main__":
    from resume_parser import parse_resume

    resume_text = parse_resume(RESUME_PATH)
    chunks = chunk_resume(resume_text)

    for section, content in chunks.items():
        print(f"=== {section} ===")
        print(content[:200])
        print()