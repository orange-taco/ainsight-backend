from datetime import datetime, timedelta
from typing import List
from ingest.sources.github.search.search_job_schema import create_job_document
from core.logging.logger import get_logger

def generate_jobs_for_backfill(
    bucket_prefix: str,
    query_template: str,
    start_date: str,  # "2022-01-01"
    end_date: str,    # "2024-12-31"
    window_days: int = 3,
) -> List[dict]:
    """
    날짜 범위를 window_days 단위로 쪼개서 job 목록 생성
    
    Example:
        jobs = generate_jobs_for_backfill(
            bucket_prefix="ml_repos",
            query_template="created:{from_date}..{to_date} stars:>20",
            start_date="2022-01-01",
            end_date="2024-12-31",
            window_days=3,
        )
    """
    logger = get_logger(__name__)
    
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    jobs = []
    current = start
    
    while current < end:
        window_end = min(current + timedelta(days=window_days), end)
        
        # bucket 네이밍: ml_repos_2022_q1
        year = current.year
        quarter = (current.month - 1) // 3 + 1
        bucket = f"{bucket_prefix}_{year}_q{quarter}"
        
        job = create_job_document(
            bucket=bucket,
            query_template=query_template,
            window_from=current.strftime("%Y-%m-%d"),
            window_to=window_end.strftime("%Y-%m-%d"),
            max_attempts=3,
        )
        
        jobs.append(job)
        current = window_end + timedelta(days=1)
    
    logger.info(f"Generated {len(jobs)} jobs from {start_date} to {end_date}")
    return jobs