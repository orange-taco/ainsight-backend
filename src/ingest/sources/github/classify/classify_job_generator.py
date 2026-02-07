from pymongo.errors import DuplicateKeyError
from ingest.sources.github.classify.classify_job_schema import create_classify_job
from core.logging.logger import get_logger

logger = get_logger(__name__)

async def generate_classify_jobs(db) -> int:
    """readme_fetched=true이고 ai_classified=false인 repo들의 job 생성"""
    repos_col = db["github_repositories"]
    jobs_col = db["github_classify_jobs"]
    
    cursor = repos_col.find(
        {
            "enrichment.readme_fetched": True,
            "enrichment.ai_classified": False
        },
        {"repo_id": 1, "full_name": 1}
    )
    
    jobs = []
    async for repo in cursor:
        jobs.append(create_classify_job(repo["repo_id"], repo["full_name"]))
    
    if not jobs:
        logger.info("No repos need classification")
        return 0
    
    inserted = 0
    skipped = 0
    for job in jobs:
        try:
            await jobs_col.insert_one(job)
            inserted += 1
        except DuplicateKeyError:
            skipped += 1
    
    logger.info(f"Classify job generation: {inserted} inserted, {skipped} skipped")
    return inserted
