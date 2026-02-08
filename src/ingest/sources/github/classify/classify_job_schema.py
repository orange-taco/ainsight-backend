from datetime import datetime, timezone
from typing import Literal

ClassifyJobStatus = Literal["pending", "running", "done", "failed"]

def create_classify_job(repo_id: int, full_name: str, max_attempts: int = 3) -> dict:
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
