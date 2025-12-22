from datetime import datetime, timezone
from typing import Literal

JobStatus = Literal["pending", "running", "done", "failed"]

def create_job_document(
    bucket: str,
    query_template: str,
    window_from: str,
    window_to: str,
    max_attempts: int = 3
) -> dict:
    """
    github_ingest_jobs 컬렉션용 document 생성
    
    Args:
        bucket: 불변 의미 기반 네이밍 (예: "ml_repos_2024_q1")
        query_template: "created:{from}..{to} stars:>20"
        window_from: "2024-01-01"
        window_to: "2024-01-03"
    """
    now = datetime.now(timezone.utc)
    
    return {
        "bucket": bucket,
        "query_template": query_template,
        "window": {
            "from": window_from,
            "to": window_to,
        },
        "status": "pending",
        "attempts": 0,
        "max_attempts": max_attempts,
        "created_at": now,
        "updated_at": now,
        "started_at": None,      # running 전환 시 기록
        "completed_at": None,    # done/failed 전환 시 기록
        "error_message": None,   # failed 시 원인 기록
        "repos_count": 0,        # 수집된 repo 개수
    }