import asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from core.logging.logger import get_logger


async def print_job_status(db: AsyncIOMotorDatabase):
    """
    Job 상태 요약 출력
    """
    jobs_col = db["github_ingest_jobs"]
    logger = get_logger(__name__)
    
    # 상태별 집계
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
    logger.info("📊 Job Status Summary")
    logger.info("=" * 60)
    logger.info(f"Total:    {total:4d}")
    logger.info(f"Pending:  {pending:4d}  ({pending/total*100:.1f}%)" if total > 0 else "Pending:     0")
    logger.info(f"Running:  {running:4d}  ({running/total*100:.1f}%)" if total > 0 else "Running:     0")
    logger.info(f"Done:     {done:4d}  ({done/total*100:.1f}%)" if total > 0 else "Done:        0")
    logger.info(f"Failed:   {failed:4d}  ({failed/total*100:.1f}%)" if total > 0 else "Failed:      0")
    logger.info("=" * 60)
    
    # Failed job 세부 정보 (최근 5개)
    if failed > 0:
        logger.info("Recent Failed Jobs:")
        failed_jobs = jobs_col.find({"status": "failed"}).sort("updated_at", -1).limit(5)
        async for job in failed_jobs:
            logger.error(
                f"  - {job['bucket']} | "
                f"{job['window']['from']} ~ {job['window']['to']} | "
                f"Error: {job.get('error_message', 'Unknown')}"
            )
        logger.info("=" * 60)


async def monitor_jobs_periodically(db: AsyncIOMotorDatabase, interval: int = 600):
    """
    주기적으로 job 상태 출력
    
    Args:
        interval: 출력 간격 (초, 기본 10분)
    """
    logger = get_logger(__name__)
    logger.info(f"Job monitor started (interval: {interval}s)")
    
    while True:
        try:
            await asyncio.sleep(interval)
            await print_job_status(db)
        except asyncio.CancelledError:
            logger.info("Job monitor stopped")
            break
        except Exception as e:
            logger.error(f"Monitor error: {e}", exc_info=True)