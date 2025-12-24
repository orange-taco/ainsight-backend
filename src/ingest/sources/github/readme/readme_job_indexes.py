# readme_job_indexes.py

from motor.motor_asyncio import AsyncIOMotorDatabase

async def ensure_readme_job_indexes(db: AsyncIOMotorDatabase):
    """github_readme_jobs 컬렉션 인덱스 생성"""
    col = db["github_readme_jobs"]

    # repo_id unique: 같은 repo에 대해 중복 job 방지
    await col.create_index(
        [("repo_id", 1)],
        unique=True,
        name="repo_id_unique",
    )

    # status + attempts + created_at: pending job을 오래된 순서로 가져오기
    # attempts 필드 (max_attempts 체크용)
    await col.create_index(
        [("status", 1), ("attempts", 1), ("created_at", 1)],
        name="status_attempts_created_asc",
    )

    # updated_at: 모니터링용
    await col.create_index(
        [("updated_at", -1)],
        name="updated_at_desc",
    )