import asyncio
import signal
from pymongo.errors import DuplicateKeyError

from core.containers.app_containers import AppContainer
from ingest.sources.github.search.search_job_indexes import ensure_search_job_indexes
from ingest.sources.github.shared.repo_indexes import ensure_repo_indexes
from ingest.sources.github.search.search_worker import GitHubJobWorker
from ingest.sources.github.search.search_job_generator import generate_jobs_for_backfill
from ingest.sources.github.search.search_job_monitor import print_job_status
from core.config.settings import settings
from core.logging.logger import get_logger

logger = get_logger(__name__)

worker_instance = None

# Global worker reference for signal handler
async def init_jobs():
    """
    Job 생성 로직
    
    전략:
    1. Active job이 있으면 → 생성 안 함 (계속 처리)
    2. Active job이 없으면 → 새로 생성
    """
    container = AppContainer()
    mongo = container.mongo_client()
    db = mongo[settings.MONGO_DB_NAME]
    jobs_col = db["github_search_jobs"]
    
    # Active job 확인
    active_count = await jobs_col.count_documents({
        "status": {"$in": ["pending", "running"]}
    })
    
    if active_count > 0:
        logger.info(
            f"Active jobs exist ({active_count} pending/running). "
            f"Continuing with existing jobs."
        )
        await print_job_status(db)
        return
    
    # Total job 확인
    total_count = await jobs_col.count_documents({})
    
    if total_count > 0:
        logger.info(
            f"All previous jobs completed or failed ({total_count} total). "
            f"Creating new jobs..."
        )
    else:
        logger.info("No jobs found. Creating initial jobs...")
    
    # Job 정의
    job_configs = [
        {
            "bucket_prefix": settings.GITHUB_INGEST_BUCKET_PREFIX,
            "query_template": settings.GITHUB_INGEST_QUERY_TEMPLATE,
            "start_date": settings.GITHUB_INGEST_START_DATE,
            "end_date": settings.GITHUB_INGEST_END_DATE,
            "window_days": settings.GITHUB_INGEST_WINDOW_DAYS,
        },
    ]
    
    total_jobs = []
    for config in job_configs:
        jobs = generate_jobs_for_backfill(**config)
        total_jobs.extend(jobs)
    
    if total_jobs:
        inserted = 0
        skipped = 0
        
        for job in total_jobs:
            try:
                await jobs_col.insert_one(job)
                inserted += 1
            except DuplicateKeyError:
                skipped += 1
        
        logger.info(
            f"Job generation complete: "
            f"{inserted} inserted, {skipped} skipped"
        )
        
        await print_job_status(db)
    else:
        logger.warning("No jobs generated")


async def run_worker():
    """Worker 실행"""
    global worker_instance

    container = AppContainer()
    mongo = container.mongo_client()
    
    worker = GitHubJobWorker(
        mongo=mongo,
        token=settings.get_github_token(),
        worker_id=settings.WORKER_ID,
        pipeline_version=settings.GITHUB_INGEST_PIPELINE_VERSION,
    )
    worker_instance = worker
    await worker.run(poll_interval=10)


async def main():
    """메인 진입점"""
    container = AppContainer()
    mongo = container.mongo_client()
    db = mongo[settings.MONGO_DB_NAME]

    logger.info("=" * 60)
    logger.info("GitHub Ingest System Starting")
    logger.info("=" * 60)

    # 인덱스 생성
    logger.info("🔧 Ensuring indexes...")
    await ensure_repo_indexes(db)
    await ensure_search_job_indexes(db)
    logger.info("Indexes ready")

    # MongoDB 연결 테스트
    await mongo.admin.command("ping")
    logger.info("MongoDB connected")

    # Job 초기화
    await init_jobs()

    # Worker 시작
    logger.info("=" * 60)
    await run_worker()


def signal_handler(signum, frame):
    global worker_instance

    logger.info(f"Received signal {signum}. Intiating graceful shucdown")
    
    if worker_instance:
        worker_instance.shutdown_requested = True

    raise SystemExit(0)


if __name__ == "__main__":
    # Signal 등록
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Docker stop
    
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown complete")