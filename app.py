import streamlit as st
import os
import time
import tempfile
from dotenv import load_dotenv
from resume_parser import parse_resume
from resume_chunker import chunk_resume
from jd_search_adzuna import (
    ADZUNA_COUNTRIES, search_all_countries, filter_data_related,
    filter_internship_only, filter_by_recency, deduplicate_by_company_title
)
from language_filter import is_accepted_language
from jd_fetcher import fetch_jd_from_url
from matcher import calculate_match
from job_store import init_db, is_seen, save_job, mark_applied, get_applied_jobs, save_and_mark_applied
from keyword_extractor import extract_keywords
from cover_letter_generator import retrieve_relevant_sections, generate_cover_letter

load_dotenv()

st.set_page_config(page_title="Job Match Assistant", layout="wide")
st.title("Job Match Assistant")
st.caption("Upload your resume -> auto-search or paste a JD manually -> get a match score -> generate a cover letter on demand")

MATCH_THRESHOLD = 0.5

# ============ Shared state across tabs ============
if "resume_text" not in st.session_state:
    st.session_state.resume_text = None
if "resume_chunks" not in st.session_state:
    st.session_state.resume_chunks = None
if "search_results" not in st.session_state:
    st.session_state.search_results = None
if "manual_result" not in st.session_state:
    st.session_state.manual_result = None

# ============ Resume upload (shared, parsed once) ============
uploaded_file = st.file_uploader("Upload your resume (PDF)", type="pdf")

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    if st.session_state.resume_text is None:
        with st.spinner("Parsing resume..."):
            st.session_state.resume_text = parse_resume(tmp_path)
            st.session_state.resume_chunks = chunk_resume(st.session_state.resume_text)
        st.success("Resume parsed. You can now use the tabs below.")

resume_ready = st.session_state.resume_text is not None

init_db()

tab1, tab2, tab3 = st.tabs(["Auto Search (Adzuna)", "Paste JD Manually", "Applied Jobs"])

# ============ Tab 1: Auto search ============
with tab1:
    with st.sidebar:
        st.header("Search settings")
        selected_country_names = st.multiselect(
            "Target countries",
            options=list(ADZUNA_COUNTRIES.keys()),
            default=["France", "United Kingdom"]
        )
        countries = [ADZUNA_COUNTRIES[name] for name in selected_country_names]

    if not resume_ready:
        st.info("Please upload your resume above first")
    else:
        if st.button("Search and compute match scores", type="primary"):
            with st.spinner("Searching jobs across countries..."):
                jobs = search_all_countries(countries=countries)

            jobs = filter_data_related(jobs)
            jobs = filter_internship_only(jobs)
            jobs = [j for j in jobs if is_accepted_language(j["description_snippet"])]
            jobs = filter_by_recency(jobs, max_days_old=30)
            jobs = deduplicate_by_company_title(jobs)
            new_jobs = [j for j in jobs if not is_seen(j["url"])]

            st.info(f"{len(jobs)} candidates after filtering, {len(new_jobs)} are new")

            results = []
            progress_bar = st.progress(0)

            for i, job in enumerate(new_jobs):
                full_jd, error = fetch_jd_from_url(job["url"])
                if error:
                    full_jd = job["description_snippet"]

                score = calculate_match(st.session_state.resume_text, full_jd)

                job_record = {
                    "title": job["title"], "company": job["company"],
                    "location": job["location"], "url": job["url"],
                    "score": score, "full_jd": full_jd
                }
                save_job({k: v for k, v in job_record.items() if k != "full_jd"})

                if score >= MATCH_THRESHOLD:
                    results.append(job_record)

                progress_bar.progress((i + 1) / max(len(new_jobs), 1))

            progress_bar.empty()
            results.sort(key=lambda x: x["score"], reverse=True)
            st.session_state.search_results = results

        if st.session_state.search_results:
            st.subheader(f"Matches ({len(st.session_state.search_results)})")

            for idx, r in enumerate(st.session_state.search_results):
                with st.container(border=True):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**{r['title']}**")
                        st.caption(f"{r['company']} - {r['location']}")
                    with col2:
                        st.metric("Match score", f"{r['score']:.3f}")

                    st.markdown(f"[View original posting]({r['url']})")

                    letter_key = f"auto_letter_{idx}"

                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("Generate cover letter", key=f"auto_gen_btn_{idx}"):
                            with st.spinner("Extracting keywords and generating cover letter..."):
                                keywords = extract_keywords(r["full_jd"])
                                relevant_sections = retrieve_relevant_sections(
                                    keywords, st.session_state.resume_chunks
                                )
                                applicant_name = st.session_state.resume_chunks["HEADER"].split("\n")[0].strip()

                                letter = generate_cover_letter(
                                    r["full_jd"], keywords, relevant_sections,
                                    applicant_name=applicant_name,
                                    company_name=r["company"]
                                )
                                st.session_state[letter_key] = letter

                    with col_b:
                        if st.button("Mark as applied", key=f"auto_applied_btn_{idx}"):
                            mark_applied(r["url"])
                            st.success(f"Marked as applied: {r['title']}")

                    if letter_key in st.session_state:
                        with st.expander("View generated cover letter", expanded=False):
                            st.text_area("Cover letter", st.session_state[letter_key],
                                         height=300, key=f"auto_display_{idx}",
                                         label_visibility="collapsed")

# ============ Tab 2: Manual JD paste ============
with tab2:
    st.caption("For platforms without API access (e.g. LinkedIn): paste the JD text and run the same matching and generation pipeline")

    if not resume_ready:
        st.info("Please upload your resume above first")
    else:
        col1, col2 = st.columns(2)
        with col1:
            manual_company = st.text_input("Company name", key="manual_company_input")
        with col2:
            manual_title = st.text_input("Job title (optional)", key="manual_title_input")

        manual_url = st.text_input("Original job posting URL (optional)", key="manual_url_input")
        manual_jd_text = st.text_area("Paste the full job description (JD)", height=250, key="manual_jd_input")

        if st.button("Analyze match score", type="primary", key="manual_analyze_btn"):
            if not manual_jd_text.strip():
                st.warning("Please paste the JD content first")
            elif not manual_company.strip():
                st.warning("Please fill in the company name (needed for cover letter generation)")
            else:
                with st.spinner("Computing match score..."):
                    score = calculate_match(st.session_state.resume_text, manual_jd_text)

                st.session_state.manual_result = {
                    "company": manual_company,
                    "title": manual_title if manual_title.strip() else "Untitled position",
                    "url": manual_url.strip(),
                    "jd_text": manual_jd_text,
                    "score": score
                }

        if st.session_state.manual_result:
            r = st.session_state.manual_result
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{r['title']}**")
                    st.caption(r["company"])
                with col2:
                    st.metric("Match score", f"{r['score']:.3f}")

                if r["score"] < MATCH_THRESHOLD:
                    st.warning(f"Match score is below the suggested threshold ({MATCH_THRESHOLD}); the cover letter may be less targeted, but you can still generate one")

                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("Generate cover letter", key="manual_gen_btn"):
                        with st.spinner("Extracting keywords and generating cover letter..."):
                            keywords = extract_keywords(r["jd_text"])
                            relevant_sections = retrieve_relevant_sections(
                                keywords, st.session_state.resume_chunks
                            )
                            applicant_name = st.session_state.resume_chunks["HEADER"].split("\n")[0].strip()

                            letter = generate_cover_letter(
                                r["jd_text"], keywords, relevant_sections,
                                applicant_name=applicant_name,
                                company_name=r["company"]
                            )
                            st.session_state.manual_letter = letter

                with col_b:
                    if st.button("Mark as applied", key="manual_applied_btn"):
                        # No URL was provided -> build a unique fallback key so this
                        # doesn't collide with any other manually-added record
                        job_url = r["url"] if r["url"] else f"manual-{r['company']}-{r['title']}-{int(time.time())}"
                        job_record = {
                            "title": r["title"], "company": r["company"],
                            "location": "N/A", "url": job_url, "score": r["score"]
                        }
                        save_and_mark_applied(job_record)
                        st.success(f"Marked as applied: {r['title']}")

                if "manual_letter" in st.session_state:
                    with st.expander("View generated cover letter", expanded=False):
                        st.text_area("Cover letter", st.session_state.manual_letter,
                                     height=300, key="manual_display",
                                     label_visibility="collapsed")

# ============ Tab 3: Applied jobs overview ============
with tab3:
    st.caption("All jobs you've marked as applied")

    applied_jobs = get_applied_jobs()

    if not applied_jobs:
        st.info("No applications recorded yet")
    else:
        st.write(f"Total applied: {len(applied_jobs)}")
        for row in applied_jobs:
            url, title, company, location, score, first_seen_date, applied = row
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.caption(f"{company} - {location} - Score: {score:.3f} - First seen: {first_seen_date}")
                if not url.startswith("manual-"):
                    st.markdown(f"[Original posting]({url})")