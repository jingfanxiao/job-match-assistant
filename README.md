# Job Match Assistant

An automated job search pipeline that searches multiple European job boards, filters postings by domain relevance and language, computes semantic similarity between a candidate's resume and job descriptions using embeddings, and stores results locally to avoid redundant processing across runs.

Built as a personal tool to streamline the internship search process for data science / AI roles, with a focus on transparent, explainable matching rather than a black-box scoring system.

## Features

- **Multi-country job search** via the Adzuna API, covering markets across Europe
- **Two-stage relevance filtering**: domain filtering (data-related roles) and role-type filtering (internships/apprenticeships only, excluding senior positions)
- **Language detection** to retain only English or French postings, regardless of the country the job is listed in
- **Semantic matching** between resume and job description using sentence embeddings and cosine similarity
- **Persistent deduplication** via SQLite — previously checked postings are skipped on subsequent runs, saving API calls and avoiding repeated review of the same job
- **PDF resume parsing** with cleanup for common extraction artifacts (missing spaces from font kerning, duplicated characters from decorative fonts)

## Tech Stack

| Component | Choice | Notes |
|---|---|---|
| LLM | DeepSeek V4-Flash (via SiliconFlow API) | Used for structured JD keyword extraction |
| Embeddings | BAAI/bge-m3 (via SiliconFlow API) | Multilingual, handles English/French text |
| Job data source | Adzuna API | Free tier, official developer API, covers ~16 European markets |
| Frontend | Streamlit | Rapid prototyping for the demo interface |
| Storage | SQLite | Lightweight, file-based, sufficient for single-user deduplication tracking |
| PDF parsing | pdfplumber | Text extraction with tolerance tuning for layout artifacts |
| Web content extraction | trafilatura | Extracts clean article text from job posting pages |
| Language detection | langdetect | Lightweight language identification for filtering |

**Design decision:** No vector database (e.g. Pinecone, ChromaDB) is used. Given the batch size involved (tens of job postings per run, not millions of documents), computing cosine similarity directly with NumPy is simpler and avoids unnecessary infrastructure.

## How It Works

```
Resume (PDF)
    │
    ▼
Parse & clean text ──────────────┐
                                  │
Adzuna search (multi-country) ───┤
    │                            │
    ▼                            │
Domain filter (data-related)     │
    │                            │
    ▼                            │
Role-type filter (internships    │
only, exclude senior roles)      │
    │                            │
    ▼                            │
Language filter (EN/FR only)     │
    │                            │
    ▼                            │
Deduplication (SQLite lookup)    │
    │                            │
    ▼                            │
Fetch full JD text               │
    │                            │
    ▼                            ▼
        Cosine similarity (embeddings)
                │
                ▼
        Filter by threshold, rank, display
                │
                ▼
        Save results to SQLite (all checked jobs, not just matches)
```

## Getting Started

### Prerequisites

- Python 3.10+
- API keys for [SiliconFlow](https://siliconflow.cn) (LLM + embeddings) and [Adzuna](https://developer.adzuna.com) (job search)

### Installation

```bash
git clone https://github.com/<your-username>/job-match-assistant.git
cd job-match-assistant
pip install -r requirements.txt
```

### Configuration

Copy the example environment file and fill in your own credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```
SILICONFLOW_API_KEY=your_key_here
ADZUNA_APP_ID=your_app_id_here
ADZUNA_APP_KEY=your_app_key_here
RESUME_PATH=resume.pdf
```

Place your own resume PDF in the project root (or point `RESUME_PATH` to its location).

### Run

```bash
streamlit run app.py
```

Or run the search pipeline directly from the command line:

```bash
python job_matcher.py
```

## Project Structure

```
├── app.py                  # Streamlit interface
├── resume_parser.py        # PDF text extraction and cleanup
├── resume_chunker.py       # Splits resume into sections (education, projects, etc.)
├── jd_search_adzuna.py     # Multi-country job search + domain/role filtering
├── jd_fetcher.py           # Fetches full job description text from a URL
├── keyword_extractor.py    # LLM-based structured keyword extraction from JDs
├── language_filter.py      # Language detection filtering (EN/FR)
├── matcher.py               # Embedding generation and cosine similarity
├── job_store.py             # SQLite storage and deduplication logic
├── job_matcher.py           # Main pipeline orchestrating all steps above
├── requirements.txt
├── .env.example
└── README.md
```

## Known Limitations

- **Character-cleaning regex** for decorative PDF fonts can occasionally over-compress legitimate double letters in acronyms (e.g. "ANSSI" → "ANSI"). This is a precision/recall tradeoff; a whitelist of known exceptions would be the next improvement.
- **Language detection operates on the job posting text itself**, not on the actual working language required for the role. A posting written in English could still require fluency in another language for client-facing work.
- **Section-splitting for resumes** relies on a fixed list of common header names. Resumes with unconventional formatting or headers outside this list may not be split accurately.
- **No matching threshold is backed by published research** — cosine similarity values are highly dependent on the specific embedding model used, so the threshold here was calibrated empirically against known relevant/irrelevant examples rather than borrowed from literature calibrated on a different model.
- **Application submission is intentionally manual.** The pipeline surfaces matched postings and their original links; it does not auto-submit applications, both to avoid violating job board terms of service and because most applications require answering platform-specific custom questions that benefit from human judgment.

## Roadmap

- [ ] LLM-generated, JD-tailored cover letters (retrieval over resume sections + keyword-targeted generation)
- [ ] Agent-based tool orchestration (LangChain) to let the system decide autonomously whether a posting is worth generating materials for
- [ ] Interview question preparation based on extracted JD keywords
- [ ] Source citation in generated content, linking claims back to specific resume sections
- [ ] Additional data sources: France Travail (official French employment API), EURES (EU-wide job mobility portal)

## License

MIT
