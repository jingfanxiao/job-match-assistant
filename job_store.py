import sqlite3
from datetime import datetime

DB_PATH = "jobs.db"


def init_db():
    """初始化数据库,如果表不存在则创建"""
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
    """检查某个岗位URL是否已经在数据库中(即之前检查过)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT url FROM jobs WHERE url = ?", (url,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def save_job(job):
    """
    存入一个岗位记录。
    无论匹配度是否达标都应该存,避免下次重复抓取和计算,节省API调用。
    INSERT OR IGNORE: 如果url已存在(主键冲突),静默跳过,不报错。
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
    """把某个岗位标记为已投递(供后续手动确认投递后调用)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET applied = 1 WHERE url = ?", (url,))
    conn.commit()
    conn.close()


def get_all_jobs():
    """获取数据库里所有记录,按匹配分数从高到低排序"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY score DESC")
    results = cursor.fetchall()
    conn.close()
    return results


def get_stats():
    """返回一些基础统计信息,方便调试和展示"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM jobs")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE applied = 1")
    applied = cursor.fetchone()[0]
    conn.close()
    return {"total_jobs_checked": total, "total_applied": applied}


if __name__ == "__main__":
    # ---- 测试流程 ----
    init_db()
    print("数据库初始化完成\n")

    # 模拟第一次运行:存入两条测试数据
    test_job_1 = {
        "url": "https://test.com/job1",
        "title": "Data Science Intern (测试用)",
        "company": "Test Company A",
        "location": "Paris",
        "score": 0.65
    }
    test_job_2 = {
        "url": "https://test.com/job2",
        "title": "Machine Learning Intern (测试用)",
        "company": "Test Company B",
        "location": "London",
        "score": 0.42
    }

    print("=== 第一次运行:存入2条测试数据 ===")
    for job in [test_job_1, test_job_2]:
        if is_seen(job["url"]):
            print(f"跳过(已存在): {job['title']}")
        else:
            save_job(job)
            print(f"新存入: {job['title']}")

    print(f"\n当前统计: {get_stats()}")

    # 模拟第二次运行:再次尝试存入同样的数据,验证去重是否生效
    print("\n=== 模拟第二次运行:再次尝试存入相同数据 ===")
    for job in [test_job_1, test_job_2]:
        if is_seen(job["url"]):
            print(f"✅ 正确跳过(已存在): {job['title']}")
        else:
            save_job(job)
            print(f"❌ 不应该出现: 重复存入了 {job['title']}")

    print(f"\n最终统计: {get_stats()}")
    print("\n=== 数据库中所有记录 ===")
    for row in get_all_jobs():
        print(row)