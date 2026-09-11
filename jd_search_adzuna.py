import requests
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from language_filter import is_accepted_language

load_dotenv()

APP_ID = os.getenv("ADZUNA_APP_ID")
APP_KEY = os.getenv("ADZUNA_APP_KEY")

# Full name -> two-letter Adzuna country code. API calls require the code;
# the dict key (full name) is used for readability and UI display.
# Luxembourg is not covered by Adzuna.
ADZUNA_COUNTRIES = {
    "United Kingdom": "gb",
    "France": "fr",
    "Germany": "de",
    "Austria": "at",
    "Belgium": "be",
    "Switzerland": "ch",
    "Spain": "es",
    "Australia": "au",
    "Brazil": "br",
    "Canada": "ca",
    "India": "in",
    "Italy": "it",
    "Mexico": "mx",
    "Netherlands": "nl",
    "New Zealand": "nz",
    "Poland": "pl",
    "Singapore": "sg",
    "United States": "us",
    "South Africa": "za",
}

# Query pairs requiring all terms to co-occur (what_and), covering EN/FR
# internship phrasing. Does not cover "stagiaire" or "alternance" (apprenticeship);
# more variants could be added but at the cost of more API calls.
SEARCH_QUERIES = [
    "data internship",
    "data stage",
    "AI internship",
    "AI stage",
    "machine learning internship",
    "machine learning stage",
]


def search_adzuna(query, country="fr", results_per_page=20):
    """
    Call the Adzuna search endpoint for one country and one query.
    Returns a list of job dicts; returns [] on failure instead of raising,
    so batch loops don't get interrupted by a single failed request.
    """
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    params = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "results_per_page": results_per_page,
        "what_and": query,
        "content-type": "application/json"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ {country} [{query}] request failed, status: {response.status_code}")
            return []
        data = response.json()
    except Exception as e:
        print(f"⚠️ {country} [{query}] search error: {e}")
        return []

    jobs = []
    for item in data.get("results", []):
        jobs.append({
            "title": item.get("title"),
            "company": item.get("company", {}).get("display_name"),
            "location": item.get("location", {}).get("display_name"),
            "country": country,
            "description_snippet": item.get("description"),
            "url": item.get("redirect_url"),
            "created": item.get("created")
        })

    return jobs


def search_all_countries(countries=None, queries=None, results_per_page=20):
    """
    Search across multiple countries and query terms, merging all results.
    Call count = len(countries) * len(queries) — watch Adzuna's free tier (1000/month).
    """
    countries = countries if countries is not None else list(ADZUNA_COUNTRIES.values())
    queries = queries if queries is not None else SEARCH_QUERIES

    all_jobs = []
    total_calls = 0

    for country in countries:
        for query in queries:
            jobs = search_adzuna(query, country=country, results_per_page=results_per_page)
            total_calls += 1
            print(f"{country} [{query}]: {len(jobs)} jobs found")
            all_jobs.extend(jobs)

    print(f"\n{total_calls} API calls made, {len(all_jobs)} jobs total (before dedup)")
    return all_jobs


def filter_data_related(jobs):
    """
    Keep only postings genuinely related to data/AI.
    Checking for the bare word "data" alone is too broad — it false-positives on
    GDPR boilerplate ("we process your personal data..."), so title is checked first
    (cleaner signal, rarely contains boilerplate), and more specific phrases are used
    for the description fallback check.
    """
    title_keywords = ["data", "machine learning", "ml ", "ai ", " ai",
                       "analytics", "statistique", "données",
                       "intelligence artificielle", "data scien", "datascien"]

    description_phrases = ["data scien", "data analy", "data engineer",
                            "machine learning", "deep learning",
                            "science des données", "analyse de données",
                            "ingénieur data", "intelligence artificielle"]

    filtered = []
    for job in jobs:
        title_lower = job["title"].lower()
        desc_lower = job["description_snippet"].lower()

        title_match = any(kw in title_lower for kw in title_keywords)
        desc_match = any(phrase in desc_lower for phrase in description_phrases)

        if title_match or desc_match:
            filtered.append(job)

    return filtered


def filter_internship_only(jobs):
    """
    Keep only genuine internships/stages, excluding apprenticeships (alternance).
    Apprenticeships in the UK/France are typically long-term, formally employed
    positions — different from the short-term stage agreement a Master's student needs.
    """
    internship_keywords = ["intern", "internship", "stage", "stagiaire"]

    exclude_keywords = ["apprentice", "apprenticeship", "alternance",
                         "senior", "distinguished", "lead", "director",
                         "head of", "principal", "architect", "manager"]

    filtered = []
    for job in jobs:
        title_lower = job["title"].lower()

        has_internship_term = any(kw in title_lower for kw in internship_keywords)
        has_exclude_term = any(kw in title_lower for kw in exclude_keywords)

        if has_internship_term and not has_exclude_term:
            filtered.append(job)

    return filtered


def filter_by_recency(jobs, max_days_old=30):
    """
    Keep only postings indexed within the last max_days_old days.
    Note: Adzuna's "created" field reflects when Adzuna indexed the posting,
    which can lag behind the actual posting date — an inherent limitation of
    aggregator data that filtering can only partially mitigate.
    """
    now = datetime.now(timezone.utc)
    filtered = []

    for job in jobs:
        created_str = job.get("created")
        if not created_str:
            continue
        try:
            created_date = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            days_old = (now - created_date).days
            if days_old <= max_days_old:
                filtered.append(job)
        except (ValueError, TypeError):
            continue  # unparseable date, exclude conservatively

    return filtered


def deduplicate_by_company_title(jobs):
    """
    Deduplicate postings that share the same company + title, keeping the first.
    Observed in practice: Adzuna's /land/ad/ links for the same role posted across
    multiple locations often land on the same underlying page, unlike /details/
    links, which usually represent genuinely distinct postings.
    """
    seen_combos = set()
    filtered = []

    for job in jobs:
        combo_key = (job["company"].strip().lower(), job["title"].strip().lower())
        if combo_key not in seen_combos:
            seen_combos.add(combo_key)
            filtered.append(job)

    return filtered


if __name__ == "__main__":
    test_countries = ["fr", "gb"]

    jobs = search_all_countries(countries=test_countries)

    print(f"\nBefore filtering: {len(jobs)} jobs")
    jobs = filter_data_related(jobs)
    print(f"After data-relevance filter: {len(jobs)} jobs")

    jobs = filter_internship_only(jobs)
    print(f"After internship-only filter: {len(jobs)} jobs")

    jobs = [j for j in jobs if is_accepted_language(j["description_snippet"])]
    print(f"After language filter (EN/FR): {len(jobs)} jobs")

    jobs = filter_by_recency(jobs, max_days_old=30)
    print(f"After recency filter (30 days): {len(jobs)} jobs")

    jobs = deduplicate_by_company_title(jobs)
    print(f"After dedup (company + title): {len(jobs)} jobs\n")

    print("=== Preview (first 10) ===")
    for job in jobs[:10]:
        print(f"[{job['country']}] {job['title']} — {job['company']} — {job['location']}")
        print(f"Posted: {job['created']}")
        print(f"URL: {job['url']}")
        print("---")