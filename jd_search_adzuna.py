import requests
from language_filter import is_accepted_language
import os
from dotenv import load_dotenv
# ============ 配置 ============

load_dotenv()

APP_ID = os.getenv("ADZUNA_APP_ID")
APP_KEY = os.getenv("ADZUNA_APP_KEY")

# Adzuna支持的国家代码(已知的16个左右主要市场)
# 注意: 部分代码可能在实际调用时返回0结果或报错(取决于该国家Adzuna数据覆盖情况),
# search_adzuna已做容错处理,遇到失败会跳过并打印提示,不会中断整体流程
ADZUNA_COUNTRIES = [
    "gb", "fr", "de", "at", "au", "br", "ca", "in",
    "it", "mx", "nl", "nz", "pl", "sg", "us", "za"
]

# 两组"必须同时出现"的关键词组合,分别覆盖英语/法语的"实习"表述
# what_and 要求所有词都出现在JD中,用来同时满足"data领域" + "是实习"两个条件
# 局限性: 未覆盖"stagiaire"(实习生身份词)、"alternance"(学徒制)等表述,
# 后续如需扩大覆盖面可追加更多查询组合,但会增加API调用次数
SEARCH_QUERIES = [
    "data internship",   # 英语场景: data相关 + internship
    "data stage",         # 法语场景: data相关 + stage(实习)
]


# ============ 核心函数 ============

def search_adzuna(query, country="fr", results_per_page=20):
    """
    对单个国家、单个查询词组合调用Adzuna搜索接口。

    query: 字符串,传给what_and参数,要求所有词同时出现在JD中
    country: 两位国家代码,如 "fr", "gb"
    results_per_page: 单次请求返回的结果数量上限

    返回: 岗位字典列表,失败时返回空列表(不抛出异常,便于批量循环时容错)
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
            print(f"⚠️ {country} [{query}] 请求失败,状态码: {response.status_code}")
            return []
        data = response.json()
    except Exception as e:
        print(f"⚠️ {country} [{query}] 搜索异常: {e}")
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
    跨多个国家、多组查询词批量搜索,合并所有结果。

    countries: 国家代码列表,默认用 ADZUNA_COUNTRIES 全量
    queries: 查询词列表,默认用 SEARCH_QUERIES 全量

    调用次数 = len(countries) * len(queries),注意Adzuna免费额度是1000次/月
    """
    countries = countries if countries is not None else ADZUNA_COUNTRIES
    queries = queries if queries is not None else SEARCH_QUERIES

    all_jobs = []
    total_calls = 0

    for country in countries:
        for query in queries:
            jobs = search_adzuna(query, country=country, results_per_page=results_per_page)
            total_calls += 1
            print(f"{country} [{query}]: 找到 {len(jobs)} 个岗位")
            all_jobs.extend(jobs)

    print(f"\n共调用 {total_calls} 次API,合计(未去重) {len(all_jobs)} 个岗位")
    return all_jobs
def filter_data_related(jobs):
    """
    对Adzuna返回的结果做二次过滤,只保留真正data相关的岗位。
    
    设计说明: 单纯检测"data"这个词太宽泛,几乎所有JD都会因为
    GDPR隐私声明模板("we process your personal data...")而误命中。
    因此优先检查标题(标题不太会出现这种模板文字,信号更干净),
    同时用更具体的词组代替单字"data",减少误判。
    """
    title_keywords = ["data", "machine learning", "ml ", "ai ", " ai", 
                       "analytics", "statistique", "données", 
                       "intelligence artificielle", "data scien", "datascien"]
    
    # 用于在描述里兜底检查的更具体短语(避免单字"data"造成的误判)
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
    在data相关过滤之后,再加一层过滤,确保标题里明确表明是实习/学徒制岗位,
    排除资历要求高的正式职位(如Senior/Lead/Architect/Distinguished等)。
    """
    internship_keywords = ["intern", "internship", "stage", "stagiaire", 
                            "apprentice", "apprenticeship", "alternance"]
    
    seniority_exclude = ["senior", "distinguished", "lead", "director", 
                          "head of", "principal", "architect", "manager"]
    
    filtered = []
    for job in jobs:
        title_lower = job["title"].lower()
        
        has_internship_term = any(kw in title_lower for kw in internship_keywords)
        has_seniority_term = any(kw in title_lower for kw in seniority_exclude)
        
        if has_internship_term and not has_seniority_term:
            filtered.append(job)
    
    return filtered

# ============ 测试入口 ============

if __name__ == "__main__":
    test_countries = ["fr", "gb"]

    jobs = search_all_countries(countries=test_countries)

    print(f"\n过滤前: {len(jobs)} 个岗位")
    jobs = filter_data_related(jobs)
    print(f"data相关过滤后: {len(jobs)} 个岗位")
    
    jobs = [j for j in jobs if is_accepted_language(j["description_snippet"])]
    print(f"语言过滤后(英/法): {len(jobs)} 个岗位\n")

    print(f"=== 测试结果预览(前10条) ===")
    for job in jobs[:10]:
        print(f"[{job['country']}] {job['title']} — {job['company']} — {job['location']}")
        print(f"链接: {job['url']}")
        print("---")


