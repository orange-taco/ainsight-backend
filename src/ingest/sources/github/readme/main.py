import asyncio
import signal

from core.containers.app_containers import AppContainer
from ingest.sources.github.shared.repo_indexes import ensure_repo_indexes
from ingest.sources.github.readme.readme_job_indexes import ensure_readme_job_indexes
from ingest.sources.github.readme.readme_worker import ReadmeWorker
from ingest.sources.github.readme.readme_job_generator import generate_readme_jobs
from core.config.settings import settings
from core.logging.logger import get_logger

logger = get_logger(__name__)

# Global worker reference for signal handler
worker_instance = None

async def init_jobs(db):
    """
    README job 생성 로직
    
    전략:
    1. Active job이 있으면 → 생성 안 함
    2. Active job이 없으면 → github_repositories에서 readme_fetched=false인 것들로 생성
    """
    jobs_col = db["github_readme_jobs"]
    
    # Active job 확인
    active_count = await jobs_col.count_documents({
        "status": {"$in": ["pending", "running"]}
    })
    
    if active_count > 0:
        logger.info(
            f"Active jobs exist ({active_count} pending/running). "
            f"Continuing with existing jobs."
        )
        return
    
    # Total job 확인
    total_count = await jobs_col.count_documents({})
    
    if total_count > 0:
        logger.info(
            f"All previous jobs completed ({total_count} total). "
            f"Creating new jobs..."
        )
    else:
        logger.info("No jobs found. Creating initial jobs...")
    
    # Job 생성
    inserted = await generate_readme_jobs(db, batch_size=10000)
    
    if inserted > 0:
        logger.info(f"Created {inserted} README jobs")
    else:
        logger.info("No repos need README fetching")


async def print_job_status(db):
    """Job 상태 요약 출력"""
    jobs_col = db["github_readme_jobs"]
    
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
    no_readme = status_counts.get("no_readme", 0)
    
    logger.info("=" * 60)
    logger.info("📊 README Job Status Summary")
    logger.info("=" * 60)
    logger.info(f"Total:      {total:6d}")
    logger.info(f"Pending:    {pending:6d}  ({pending/total*100:.1f}%)" if total > 0 else "Pending:        0")
    logger.info(f"Running:    {running:6d}  ({running/total*100:.1f}%)" if total > 0 else "Running:        0")
    logger.info(f"Done:       {done:6d}  ({done/total*100:.1f}%)" if total > 0 else "Done:           0")
    logger.info(f"No README:  {no_readme:6d}  ({no_readme/total*100:.1f}%)" if total > 0 else "No README:      0")
    logger.info(f"Failed:     {failed:6d}  ({failed/total*100:.1f}%)" if total > 0 else "Failed:         0")
    logger.info("=" * 60)


async def run_worker():
    global worker_instance

    """Worker 실행"""
    container = AppContainer()
    mongo = container.mongo_client()
    
    worker = ReadmeWorker(
        mongo=mongo,
        token=settings.get_github_token(),
        worker_id=settings.WORKER_ID,
        total_workers=settings.TOTAL_WORKERS,
    )
    worker_instance=worker
    
    await worker.run(poll_interval=10)

def signal_handler(signum, frame):
    """Signal 처리 (Ctrl+C, Docker stop 등)"""
    global worker_instance
    
    logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
    
    if worker_instance:
        worker_instance.shutdown_requested = True
    
    raise SystemExit(0)
    
async def main():
    """메인 진입점"""
    container = AppContainer()
    mongo = container.mongo_client()
    db = mongo[settings.MONGO_DB_NAME]

    logger.info("=" * 60)
    logger.info("GitHub README Enrichment System Starting")
    logger.info("=" * 60)

    # 인덱스 생성
    logger.info("🔧 Ensuring indexes...")
    await ensure_repo_indexes(db)
    await ensure_readme_job_indexes(db)
    logger.info("Indexes ready")

    # MongoDB 연결 테스트
    await mongo.admin.command("ping")
    logger.info("MongoDB connected")

    # Job 초기화
    await init_jobs(db)
    await print_job_status(db)

    # Worker 시작
    logger.info("=" * 60)
    await run_worker()


def signal_handler(signum, frame):
    """Signal 처리 (Ctrl+C, Docker stop 등)"""
    logger.info(f"Received signal {signum}. Shutting down...")
    raise SystemExit(0)


if __name__ == "__main__":
    # Signal 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown complete")