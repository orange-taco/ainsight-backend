async def ensure_classify_job_indexes(db):
    jobs_col = db["github_classify_jobs"]
    await jobs_col.create_index("repo_id", unique=True)
    await jobs_col.create_index([("status", 1), ("created_at", 1)])
