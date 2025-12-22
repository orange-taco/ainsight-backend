# src/ingest/sources/github/filters.py

from datetime import datetime, timedelta, timezone
from github.Repository import Repository


BLACKLIST_NAME_KEYWORDS = [
    "awesome",
    "tutorial",
    "example",
    "course",
    "bootcamp",
    "roadmap",
]


README_KEYWORDS = [
    "install",
    "usage",
    "api",
    "example",
    "documentation",
]


def is_valid_repo(repo: Repository,
    min_stars: int = 20,
    min_size: int = 50,
    min_pushed_at: int = 180,
) -> bool:
    """
    Repo-level heuristic filter
    """

    # 기본 품질
    if repo.stargazers_count < min_stars:
        return False
    if repo.size < min_size:  # KB
        return False
    if repo.fork or repo.archived:
        return False

    # 활동성
    if repo.pushed_at:
        now_utc = datetime.now(timezone.utc)
        if repo.pushed_at < now_utc - timedelta(days=min_pushed_at):
            return False

    # 이름 필터
    name = repo.name.lower()
    if any(bad in name for bad in BLACKLIST_NAME_KEYWORDS):
        return False

    return True


def is_meaningful_readme(content: str, min_length: int = 500) -> bool:
    """
    README quality heuristic
    """
    text = content.lower()

    if len(text) < min_length:
        return False

    return any(keyword in text for keyword in README_KEYWORDS)
