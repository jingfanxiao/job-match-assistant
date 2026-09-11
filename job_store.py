import sqlite3
from datetime import datetime

DB_PATH = "jobs.db"


def init_db():
    """Create the jobs table if it doesn't exist yet."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            url TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            score REAL,
            first_seen_date TEXT,
            applied INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def is_seen(url):
    """Check whether a job URL has already been stored (i.e. previously checked)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT url FROM jobs WHERE url = ?", (url,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def save_job(job):
    """
    Store a job record. Save regardless of whether the score meets the threshold,
    to avoid re-fetching and re-scoring the same job on the next run.
    INSERT OR IGNORE silently skips if the url (primary key) already exists.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO jobs (url, title, company, location, score, first_seen_date, applied)
        VALUES (?, ?, ?, ?, ?, ?, 0)
    """, (
        job["url"], job["title"], job["company"], job["location"],
        job["score"], datetime.now().strftime("%Y-%m-%d")
    ))
    conn.commit()
    conn.close()


def mark_applied(url):
    """Mark a job as applied to (call after manually confirming an application)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET applied = 1 WHERE url = ?", (url,))
    conn.commit()
    conn.close()


def get_all_jobs():
    """Return all stored records, sorted by score descending."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY score DESC")
    results = cursor.fetchall()
    conn.close()
    return results


def get_stats():
    """Basic counts for debugging/display."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM jobs")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE applied = 1")
    applied = cursor.fetchone()[0]
    conn.close()
    return {"total_jobs_checked": total, "total_applied": applied}


if __name__ == "__main__":
    init_db()
    print("Database initialized\n")

    test_job_1 = {
        "url": "https://test.com/job1",
        "title": "Data Science Intern (test)",
        "company": "Test Company A",
        "location": "Paris",
        "score": 0.65
    }
    test_job_2 = {
        "url": "https://test.com/job2",
        "title": "Machine Learning Intern (test)",
        "company": "Test Company B",
        "location": "London",
        "score": 0.42
    }

    print("=== First run: insert 2 test records ===")
    for job in [test_job_1, test_job_2]:
        if is_seen(job["url"]):
            print(f"Skipped (already exists): {job['title']}")
        else:
            save_job(job)
            print(f"Inserted: {job['title']}")

    print(f"\nCurrent stats: {get_stats()}")

    # Simulate a second run to confirm dedup works
    print("\n=== Simulated second run: re-insert same data ===")
    for job in [test_job_1, test_job_2]:
        if is_seen(job["url"]):
            print(f"Correctly skipped (already exists): {job['title']}")
        else:
            save_job(job)
            print(f"UNEXPECTED: duplicate insert of {job['title']}")

    print(f"\nFinal stats: {get_stats()}")
    print("\n=== All records in DB ===")
    for row in get_all_jobs():
        print(row)