import streamlit as st
from resume_parser import parse_resume
from jd_search_adzuna import search_adzuna
from jd_fetcher import fetch_jd_from_url
from matcher import calculate_match
import tempfile

st.set_page_config(page_title="求职匹配助手", layout="wide")
st.title("🎯 求职匹配助手 - Day1 Demo")
st.caption("上传简历 → 自动搜索岗位 → 计算匹配度")

# --- 侧边栏：搜索设置 ---
with st.sidebar:
    st.header("搜索设置")
    country = st.selectbox(
        "目标国家",
        options=["fr", "gb", "ie"],
        format_func=lambda x: {"fr": "法国", "gb": "英国", "ie": "爱尔兰"}[x]
    )
    keyword = st.text_input("搜索关键词", value="data science internship")
    num_results = st.slider("搜索结果数量", 3, 20, 5)

# --- 主界面：上传简历 ---
uploaded_file = st.file_uploader("上传你的简历(PDF)", type="pdf")

if uploaded_file:
    if st.button("🔍 开始搜索并计算匹配度", type="primary"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        with st.spinner("解析简历中..."):
            resume_text = parse_resume(tmp_path)

        with st.spinner(f"在{country}搜索岗位中..."):
            jobs = search_adzuna(keyword, country=country, results_per_page=num_results)

        if not jobs:
            st.warning("没有搜索到相关岗位,试试换个关键词")
        else:
            st.success(f"找到 {len(jobs)} 个岗位,正在计算匹配度...")

            results = []
            progress_bar = st.progress(0)

            for i, job in enumerate(jobs):
                full_jd, error = fetch_jd_from_url(job["url"])
                if error:
                    full_jd = job["description_snippet"]

                score = calculate_match(resume_text, full_jd)
                results.append({
                    "title": job["title"],
                    "company": job["company"],
                    "location": job["location"],
                    "url": job["url"],
                    "score": score,
                    "full_jd": full_jd
                })
                progress_bar.progress((i + 1) / len(jobs))

            progress_bar.empty()
            results.sort(key=lambda x: x["score"], reverse=True)

            st.subheader("📊 匹配结果(按分数排序)")

            for r in results:
                with st.container(border=True):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**{r['title']}**")
                        st.caption(f"{r['company']} · {r['location']}")
                    with col2:
                        st.metric("匹配度", f"{r['score']:.3f}")

                    with st.expander("查看完整JD"):
                        st.text(r['full_jd'][:2000])

                    st.markdown(f"[原始链接]({r['url']})")