from motor.motor_asyncio import AsyncIOMotorDatabase

async def ensure_indexes(db: AsyncIOMotorDatabase):
    col = db["github_repo_raw"]

    await col.create_index(
        [("external_id", 1)],
        unique=True,
        name="external_id_unique",
    )

    await col.create_index(
        [("activity.pushed_at", -1)],
        name="pushed_at_desc",
    )
