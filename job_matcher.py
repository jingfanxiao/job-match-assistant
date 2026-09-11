import os
from dotenv import load_dotenv
from resume_parser import parse_resume
from jd_search_adzuna import (
    search_all_countries, filter_data_related, filter_internship_only,
    filter_by_recency, deduplicate_by_company_title
)
from language_filter import is_accepted_language
from jd_fetcher import fetch_jd_from_url
from matcher import calculate_match
from job_store import init_db, is_seen, save_job

load_dotenv()

MATCH_THRESHOLD = 0.5
RESUME_PATH = os.getenv("RESUME_PATH", "resume.pdf")


def find_matching_jobs(resume_path, threshold=MATCH_THRESHOLD, countries=None):
    """Full pipeline: search -> filter -> dedupe -> score -> return matches above threshold."""
    init_db()
    resume_text = parse_resume(resume_path)

    print("=== Step 1: Multi-country search ===")
    jobs = search_all_countries(countries=countries)

    print("\n=== Step 2: Data-relevance filter ===")
    jobs = filter_data_related(jobs)
    print(f"{len(jobs)} remaining")

    print("\n=== Step 2.5: Internship-only filter ===")
    jobs = filter_internship_only(jobs)
    print(f"{len(jobs)} remaining")

    print("\n=== Step 3: Language filter (EN/FR) ===")
    jobs = [j for j in jobs if is_accepted_language(j["description_snippet"])]
    print(f"{len(jobs)} remaining")

    print("\n=== Step 3.5: Recency filter (last 30 days) ===")
    jobs = filter_by_recency(jobs, max_days_old=30)
    print(f"{len(jobs)} remaining")

    print("\n=== Step 3.7: Dedup by company + title ===")
    jobs = deduplicate_by_company_title(jobs)
    print(f"{len(jobs)} remaining")

    print("\n=== Step 4: Skip already-checked jobs ===")
    new_jobs = [j for j in jobs if not is_seen(j["url"])]
    print(f"{len(jobs) - len(new_jobs)} already checked, {len(new_jobs)} new")

    print("\n=== Step 5: Fetch full JD + compute match score ===")
    today_matches = []
    for i, job in enumerate(new_jobs):
        full_jd, error = fetch_jd_from_url(job["url"])
        if error:
            full_jd = job["description_snippet"]

        score = calculate_match(resume_text, full_jd)

        job_record = {
            "title": job["title"], "company": job["company"],
            "location": job["location"], "url": job["url"], "score": score
        }
        save_job(job_record)

        status = "MATCH" if score >= threshold else "     "
        print(f"[{status}] [{score:.3f}] ({i + 1}/{len(new_jobs)}) {job['title']}")

        if score >= threshold:
            today_matches.append(job_record)

    today_matches.sort(key=lambda x: x["score"], reverse=True)
    return today_matches


if __name__ == "__main__":
    # Small country set for testing; drop `countries` to search all of ADZUNA_COUNTRIES
    results = find_matching_jobs(RESUME_PATH, countries=["fr", "gb"])

    print(f"\n\n{'=' * 50}")
    print(f"{len(results)} new job(s) found with score >= {MATCH_THRESHOLD}:")
    print("=" * 50)
    for r in results:
        print(f"\n[{r['score']:.3f}] {r['title']} — {r['company']} — {r['location']}")
        print(f"URL: {r['url']}")