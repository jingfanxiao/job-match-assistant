import re
import os
import pdfplumber
from dotenv import load_dotenv

load_dotenv()

RESUME_PATH = os.getenv("RESUME_PATH", "resume.pdf")


def clean_repeated_chars(text):
    """
    Fix character duplication caused by decorative PDF fonts (e.g. bold/shadow
    effects rendered as overlapping layers of the same text, read back as
    repeated characters). Collapses 3+ consecutive identical characters to 1.

    Heuristic fix: can occasionally over-compress legitimate repeated letters
    (e.g. in some codes or formatting), but this is rare in EN/FR resume text.
    """
    return re.sub(r'(.)\1{2,}', r'\1', text)


def fix_spacing(text):
    """
    Fix missing spaces caused by PDF font kerning, by inserting a space
    between a lowercase letter and a following uppercase letter
    (e.g. "ArtificialIntelligence" -> "Artificial Intelligence").

    Not called by default in parse_resume — the x_tolerance tuning below
    already resolves this for most resumes. Kept as a fallback utility
    for resumes with different formatting/kerning issues.
    """
    return re.sub(r'([a-z])([A-Z])', r'\1 \2', text)


def parse_resume(file_path):
    """
    Parse a PDF resume into cleaned text: extract with pdfplumber
    (tolerance tuned to reduce word-merging), then fix decorative-font
    character duplication.
    """
    raw_text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(x_tolerance=1, y_tolerance=3)
            if page_text:
                raw_text += page_text + "\n"

    if not raw_text.strip():
        raise ValueError("No text could be extracted from this PDF — it may be a scanned image or an unsupported format")

    return clean_repeated_chars(raw_text)


if __name__ == "__main__":
    text = parse_resume(RESUME_PATH)
    print(text)
    print(f"\nTotal length: {len(text)}")