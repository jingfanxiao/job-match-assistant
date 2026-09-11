import trafilatura

# Non-JD boilerplate blocks that Adzuna appends to posting pages; truncate at first match
NOISE_MARKERS = [
    "Stats pour cet emploi",
    "Comparaison de salaire",
    "Emplois similaires",  # reserved: may need more "similar jobs" markers later
]


def fetch_jd_from_url(url):
    """Fetch and clean the full JD text from a job posting URL."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            return None, "could not access the URL, may require login"

        text = trafilatura.extract(downloaded)
        if text is None or len(text) < 50:
            return None, "fetched content too short, page may require JS rendering"

        for marker in NOISE_MARKERS:
            if marker in text:
                text = text.split(marker)[0]

        return text.strip(), None
    except Exception as e:
        return None, f"failed to fetch: {str(e)}"


if __name__ == "__main__":
    url = "https://www.adzuna.fr/details/5681609308?utm_medium=api&utm_source=373870c8"
    text, error = fetch_jd_from_url(url)
    if error:
        print(f"Error: {error}")
    else:
        print("=== First 500 chars ===")
        print(text[:500])
        print("\n=== Last 500 chars ===")
        print(text[-500:])
        print(f"\nTotal length: {len(text)}")