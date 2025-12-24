from motor.motor_asyncio import AsyncIOMotorDatabase

async def ensure_repo_indexes(db: AsyncIOMotorDatabase):
    col = db["github_repositories"]


    # repo 중복 방지
    await col.create_index(
        [("repo_id", 1)],
        unique=True,
        name="repo_id_unique",
    )

    # pushed_at: 활동성 필터링용
    await col.create_index(
        [("activity.pushed_at", -1)],
        name="pushed_at_desc",
    )

    # README 수집용 인덱스
    await col.create_index(
        [("enrichment.readme_fetched", 1)],
        name="readme_fetched",
    )