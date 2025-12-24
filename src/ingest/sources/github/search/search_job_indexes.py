from motor.motor_asyncio import AsyncIOMotorDatabase

async def ensure_search_job_indexes(db: AsyncIOMotorDatabase):
    """github_search_jobs 컬렉션 인덱스 생성"""
    col = db["github_search_jobs"]

    # status + created_at: pending job을 오래된 순서로 가져오기
    await col.create_index(
        [("status", 1), ("created_at", 1)],
        name="status_created_asc",
    )

    # bucket + window: 중복 job 방지
    await col.create_index(
        [("bucket", 1), ("window.from", 1), ("window.to", 1)],
        unique=True,
        name="bucket_window_unique",
    )

    # updated_at: 모니터링용
    await col.create_index(
        [("updated_at", -1)],
        name="updated_at_desc",
    )