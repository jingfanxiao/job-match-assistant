import trafilatura

# Adzuna页面自带的非JD内容板块标记,出现这些就截断
NOISE_MARKERS = [
    "Stats pour cet emploi",
    "Comparaison de salaire",
    "Emplois similaires",  # 可能还有"相似岗位推荐"这种板块,先预留
]

def fetch_jd_from_url(url):
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            return None, "can't enter the address, maybe need to log in"
        
        text = trafilatura.extract(downloaded)
        if text is None or len(text) < 50:
            return None, "the content fetched is too short, need render"
        
        # 截断噪音部分
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
        print(f"错误: {error}")
    else:
        print(f"=== 开头 500 字 ===")
        print(text[:500])
        print(f"\n=== 末尾 500 字 ===")
        print(text[-500:])
        print(f"\n总字数: {len(text)}")