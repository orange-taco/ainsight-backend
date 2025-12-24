from datetime import datetime, timezone
from typing import Literal

ReadmeJobStatus = Literal["pending", "running", "done", "failed", "no_readme"]

def create_readme_job(
    repo_id: int,
    full_name: str,
    max_attempts: int = 3
) -> dict:
    """
    README 수집 job document 생성
    
    Args:
        repo_id: GitHub repo ID (repo_id)
        full_name: owner/repo (API 호출용)
        max_attempts: 최대 시도 횟수
    """
    now = datetime.now(timezone.utc)
    
    return {
        "repo_id": repo_id,
        "full_name": full_name,
        "status": "pending",
        "attempts": 0,
        "max_attempts": max_attempts,
        "created_at": now,
        "updated_at": now,
        "error_message": None,
    }