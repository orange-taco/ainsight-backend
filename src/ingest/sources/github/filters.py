# src/ingest/sources/github/filters.py

from datetime import datetime, timedelta, timezone
from github.Repository import Repository




def is_valid_repo(repo: Repository,
    min_size: int = 50,
    min_pushed_at: int = 30,
) -> bool:
    """
    Repo-level heuristic filter
    """

    if repo.size < min_size:  # KB
        return False
    if repo.archived:
        return False

    # 활동성
    if repo.pushed_at:
        now_utc = datetime.now(timezone.utc)
        if repo.pushed_at < now_utc - timedelta(days=min_pushed_at):
            return False

    return True

