from typing import List
from pymongo.errors import DuplicateKeyError
from ingest.sources.github.readme.readme_job_schema import create_readme_job
from core.logging.logger import get_logger

logger = get_logger(__name__)


async def generate_readme_jobs(db, batch_size: int = 10000) -> int:
    """
    github_repositories에서 readme_fetched=false인 repo들의 job 생성
    
    Args:
        db: MongoDB database
        batch_size: 한 번에 처리할 repo 개수
        
    Returns:
        생성된 job 개수
    """
    repos_col = db["github_repositories"]
    jobs_col = db["github_readme_jobs"]
    
    # readme_fetched=false인 repo 찾기
    cursor = repos_col.find(
        {"enrichment.readme_fetched": False},
        {"repo_id": 1, "full_name": 1}
    ).limit(batch_size)
    
    jobs = []
    async for repo in cursor:
        job = create_readme_job(
            repo_id=repo["repo_id"],
            full_name=repo["full_name"],
        )
        jobs.append(job)
    
    if not jobs:
        logger.info("No repos found that need README fetching")
        return 0
    
    # Bulk insert (중복 무시)
    inserted = 0
    skipped = 0
    
    for job in jobs:
        try:
            await jobs_col.insert_one(job)
            inserted += 1
        except DuplicateKeyError:
            skipped += 1
    
    logger.info(
        f"README job generation: {inserted} inserted, {skipped} skipped"
    )
    
    return inserted