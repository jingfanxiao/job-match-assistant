from resume_parser import parse_resume
from jd_search_adzuna import search_all_countries, filter_data_related
from language_filter import is_accepted_language
from jd_fetcher import fetch_jd_from_url
from matcher import calculate_match
from job_store import init_db, is_seen, save_job
from jd_search_adzuna import search_all_countries, filter_data_related, filter_internship_only

MATCH_THRESHOLD = 0.5

def find_matching_jobs(resume_path, threshold=MATCH_THRESHOLD, countries=None):
    init_db()
    resume_text = parse_resume(resume_path)

    print("=== 第1步: 多国搜索 ===")
    jobs = search_all_countries(countries=countries)

    print(f"\n=== 第2步: data领域过滤 ===")
    jobs = filter_data_related(jobs)
    print(f"剩余 {len(jobs)} 个")

    print(f"\n=== 第2.5步: 排除非实习/资深岗位 ===")
    jobs = filter_internship_only(jobs)
    print(f"剩余 {len(jobs)} 个")   

    print(f"\n=== 第3步: 语言过滤(英/法) ===")
    jobs = [j for j in jobs if is_accepted_language(j["description_snippet"])]
    print(f"剩余 {len(jobs)} 个")

    print(f"\n=== 第4步: 去重(跳过已检查过的) ===")
    new_jobs = [j for j in jobs if not is_seen(j["url"])]
    print(f"其中 {len(jobs) - len(new_jobs)} 个已检查过,跳过; {len(new_jobs)} 个是新岗位")

    print(f"\n=== 第5步: 抓取完整JD + 计算匹配度 ===")
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

        status = "✅" if score >= threshold else "  "
        print(f"{status} [{score:.3f}] ({i+1}/{len(new_jobs)}) {job['title']}")

        if score >= threshold:
            today_matches.append(job_record)

    today_matches.sort(key=lambda x: x["score"], reverse=True)
    return today_matches


if __name__ == "__main__":
    # 先用小范围国家测试,确认全链路跑通后再换成全量ADZUNA_COUNTRIES
    results = find_matching_jobs(r"C:\Users\user\Desktop\job-find-project\Jingfan XIAO - CV(En).pdf", countries=["fr", "gb"])

    print(f"\n\n{'='*50}")
    print(f"今天新发现 {len(results)} 个匹配度 >= {MATCH_THRESHOLD} 的岗位:")
    print('='*50)
    for r in results:
        print(f"\n[{r['score']:.3f}] {r['title']} — {r['company']} — {r['location']}")
        print(f"链接: {r['url']}")