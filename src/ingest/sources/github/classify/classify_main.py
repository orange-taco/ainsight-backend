import asyncio
from datetime import datetime, timezone

from core.containers.app_containers import AppContainer
from ingest.sources.github.shared.repo_indexes import ensure_repo_indexes
from ingest.sources.github.classify.classify_job_indexes import ensure_classify_job_indexes
from ingest.sources.github.classify.classify_worker import ClassifyWorker
from ingest.sources.github.classify.classify_job_generator import generate_classify_jobs
from core.config.settings import settings
from core.logging.logger import get_logger

logger = get_logger(__name__)

async def init_jobs(db):
    jobs_col = db["github_classify_jobs"]
    
    active_count = await jobs_col.count_documents({"status": {"$in": ["pending", "running"]}})
    
    if active_count > 0:
        logger.info(f"Active jobs exist ({active_count}). Continuing.")
        return
    
    total_count = await jobs_col.count_documents({})
    if total_count > 0:
        logger.info(f"All previous jobs completed ({total_count} total). Creating new jobs...")
    
    inserted = await generate_classify_jobs(db)
    logger.info(f"Created {inserted} classify jobs" if inserted > 0 else "No repos need classification")

async def print_job_status(db):
    jobs_col = db["github_classify_jobs"]
    
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    
    status_counts = {}
    async for doc in jobs_col.aggregate(pipeline):
        status_counts[doc["_id"]] = doc["count"]
    
    total = sum(status_counts.values())
    pending = status_counts.get("pending", 0)
    running = status_counts.get("running", 0)
    done = status_counts.get("done", 0)
    failed = status_counts.get("failed", 0)
    
    logger.info("=" * 60)
    logger.info("📊 Classify Job Status Summary")
    logger.info("=" * 60)
    logger.info(f"Total:    {total:6d}")
    logger.info(f"Pending:  {pending:6d}  ({pending/total*100:.1f}%)" if total > 0 else "Pending:      0")
    logger.info(f"Running:  {running:6d}  ({running/total*100:.1f}%)" if total > 0 else "Running:      0")
    logger.info(f"Done:     {done:6d}  ({done/total*100:.1f}%)" if total > 0 else "Done:         0")
    logger.info(f"Failed:   {failed:6d}  ({failed/total*100:.1f}%)" if total > 0 else "Failed:       0")
    logger.info("=" * 60)

async def cleanup_stale_running_jobs(db):
    jobs_col = db["github_classify_jobs"]
    result = await jobs_col.update_many(
        {"status": "running"},
        {"$set": {"status": "pending", "updated_at": datetime.now(timezone.utc)}}
    )
    if result.modified_count > 0:
        logger.info(f"🔧 Restored {result.modified_count} stale running jobs")

async def run_worker():
    container = AppContainer()
    mongo = container.mongo_client()
    
    # LLM client 가져오기 (AppContainer에 있다고 가정)
    llm_client = container.llm_client()
    
    worker = ClassifyWorker(
        mongo=mongo,
        llm_client=llm_client,
        worker_id=settings.WORKER_ID,
    )
    
    await worker.run(poll_interval=10)

async def main():
    container = AppContainer()
    mongo = container.mongo_client()

    logger.info("=" * 60)
    logger.info("GitHub Classify System Starting")
    logger.info("=" * 60)

    logger.info("🔧 Ensuring indexes...")
    await ensure_repo_indexes(db)
    await ensure_classify_job_indexes(db)
    logger.info("Indexes ready")

    await mongo.admin.command("ping")
    logger.info("MongoDB connected")

    await cleanup_stale_running_jobs(db)
    await init_jobs(db)
    await print_job_status(db)

    logger.info("=" * 60)
    try:
        await run_worker()
    finally:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown complete")
