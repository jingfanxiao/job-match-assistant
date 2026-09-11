from langdetect import detect, LangDetectException

ACCEPTED_LANGUAGES = ["en", "fr"]


def is_accepted_language(text):
    """
    Detect the language of a JD and accept only English or French.
    Note: this checks the language the JD is WRITTEN in, which is a proxy for,
    not a guarantee of, the actual working language required (e.g. a posting
    written in English could still require German for client-facing work).
    """
    try:
        lang = detect(text)
        return lang in ACCEPTED_LANGUAGES
    except LangDetectException:
        return False  # detection failed (e.g. text too short), exclude conservatively


if __name__ == "__main__":
    test_texts = [
        "We are looking for a data science intern...",
        "Nous recherchons un stagiaire en data science...",
        "Wir suchen einen Praktikanten für Data Science..."
    ]
    for t in test_texts:
        result = "accepted" if is_accepted_language(t) else "rejected"
        print(f"{t[:30]}... -> {result}")