import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from pymongo.errors import DuplicateKeyError
import time

from ingest.sources.github.shared.client import GitHubClient
from ingest.sources.github.shared.filters import is_valid_repo
from ingest.mappers.github_repo_mapper import map_repo
from pymongo.errors import BulkWriteError
from core.logging.logger import get_logger
from github import GithubException


class GitHubJobWorker:
    """
    Stateless worker that processes github_ingest_jobs
    """

    def __init__(self, mongo, token: str, pipeline_version: str):
        self.db = mongo["ainsight"]
        self.jobs_col = self.db["github_ingest_jobs"]
        self.repos_col = self.db["github_repo_raw"]
        self.client = GitHubClient(token)
        self.pipeline_version = pipeline_version
        self.logger = get_logger(__name__)

    async def acquire_job(self) -> Optional[dict]:
        """
        pending job을 atomic하게 가져와 running으로 변경
        """
        # Pending job 찾기
        pending_jobs = self.jobs_col.find(
            {"status": "pending"}
        ).sort("created_at", 1)
        
        async for job in pending_jobs:
            # attempts 체크
            attempts = job.get("attempts", 0)
            max_attempts = job.get("max_attempts", 3)
            
            if attempts >= max_attempts:
                # 이미 max attempts 도달 → 다음 job
                continue
            
            # Atomic update 시도
            result = await self.jobs_col.find_one_and_update(
                {
                    "_id": job["_id"],
                    "status": "pending",  # Race condition 방지
                },
                {
                    "$set": {
                        "status": "running",
                        "started_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    },
                    "$inc": {"attempts": 1},
                },
                return_document=True,
            )
            
            if result:
                # 성공적으로 획득
                return result
        
        # Pending job 없음
        return None

    async def process_job(self, job: dict):
        """
        단일 job 처리 (query 생성 → GitHub 검색 → MongoDB 저장)
        """
        job_id = job["_id"]
        bucket = job["bucket"]
        query_template = job["query_template"]
        window_from = job["window"]["from"]
        window_to = job["window"]["to"]

        # query 생성: "created:2024-01-01..2024-01-03 stars:>20"
        query = query_template.format(from_date=window_from, to_date=window_to)
        
        self.logger.info(
            f"[Job {job_id}] Processing: {query} "
            f"(attempt {job['attempts']}/{job['max_attempts']})"
        )

        try:
            # GitHub Search API 호출
            repos = self.client.search_repositories(query)
            total_count = repos.totalCount
            self.logger.info(f"Found {total_count} repos for query: {query}")

            documents = []
            for repo in repos:
                if not is_valid_repo(repo, min_size=50, min_pushed_at=30):
                    continue
                
                documents.append(
                    map_repo(
                        repo=repo,
                        query=query,
                        bucket=bucket,
                        pipeline_version=self.pipeline_version,
                    )
                )

            # MongoDB 저장
            if documents:
                try:
                    await self.repos_col.insert_many(documents, ordered=False)
                    self.logger.info(f"Inserted {len(documents)} repos")
                except BulkWriteError as e:
                    inserted = e.details.get("nInserted", 0)
                    self.logger.info(
                        f"[Job {job_id}] Inserted {inserted} repos "
                        f"(some duplicates skipped)"
                    )

            # Job 완료 처리
            await self.jobs_col.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "status": "done",
                        "completed_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                        "repos_count": len(documents),
                        "error_message": None,
                    }
                },
            )
            self.logger.info(
                f"[Job {job_id}] ✅ Completed successfully "
                f"({len(documents)} repos collected)"
            )

        except GithubException as e:
            await self._handle_github_error(job_id, job, e)

        except Exception as e:
            await self._handle_generic_error(job_id, job, e)

    async def _handle_github_error(self, job_id, job: dict, error: GithubException):
        """
        GitHub API 에러 처리 (rate limit 포함)
        """
        if error.status == 403 or error.status == 429:
            # Rate limit 초과
            reset_timestamp = int(error.headers.get("x-ratelimit-reset", 0))
            
            if reset_timestamp > 0:
                reset_time = datetime.fromtimestamp(reset_timestamp, tz=timezone.utc)
                now = datetime.now(timezone.utc)
                wait_seconds = (reset_time - now).total_seconds()
                
                self.logger.warning(
                    f"[Job {job_id}] Rate limit exceeded. "
                    f"Reset at {reset_time.strftime('%Y-%m-%d %H:%M:%S UTC')}. "
                    f"Waiting {wait_seconds:.0f} seconds..."
                )
                
                # Job을 pending으로 되돌림 (다음 worker가 reset 후 처리)
                await self.jobs_col.update_one(
                    {"_id": job_id},
                    {
                        "$set": {
                            "status": "pending",
                            "updated_at": datetime.now(timezone.utc),
                            "error_message": (
                                f"Rate limit hit at {now.strftime('%H:%M:%S')}. "
                                f"Reset at {reset_time.strftime('%H:%M:%S')}"
                            ),
                        }
                    },
                )
                
                # 현재 worker는 reset 시간까지 대기
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds + 2) 
                
                self.logger.info(f"Job {job_id} will retry after {wait_seconds} seconds")

                return

        # 그 외 GitHub 에러 (404, 422 등)
        error_msg = f"GitHub API error ({error.status}): {error.data.get('message', str(error))}"
        self.logger.error(f"[Job {job_id}] {error_msg}")
        await self._mark_job_failed(job_id, job, error_msg)

    async def _handle_generic_error(self, job_id, job: dict, error: Exception):
        """
        일반 에러 처리
        """
        error_msg = f"Unexpected error: {str(error)}"
        self.logger.error(f"[Job {job_id}] {error_msg}", exc_info=True)
        await self._mark_job_failed(job_id, job, error_msg)

    async def _mark_job_failed(self, job_id, job: dict, error_message: str):
        """
        Job을 failed로 마킹 (재시도 제한 고려)
        """
        attempts = job.get("attempts", 0)
        max_attempts = job.get("max_attempts", 3)

        if attempts >= max_attempts:
            status = "failed"
            self.logger.error(f"Job {job_id} permanently failed after {attempts} attempts")
        else:
            status = "pending"  # 재시도 가능
            self.logger.warning(f"Job {job_id} failed (attempt {attempts}/{max_attempts}), will retry")

        await self.jobs_col.update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": status,
                    "completed_at": datetime.now(timezone.utc) if status == "failed" else None,
                    "updated_at": datetime.now(timezone.utc),
                    "error_message": error_message,
                }
            },
        )

    async def run(self, poll_interval: int = 10, auto_exit: bool = True):
        """
        무한 루프로 job 처리 (Docker에서 실행)
        """
        self.logger.info("Worker started. Polling for jobs...")
        
        consecutive_empty = 0

        while True:
            try:
                job = await self.acquire_job()
                
                if job:
                    consecutive_empty = 0
                    await self.process_job(job)
                else:
                    consecutive_empty += 1
                    if auto_exit:
                        active_count = await self.jobs_col.count_documents({
                            "status": {"$in": ["pending", "running"]}
                        })
                        if active_count == 0:
                            self.logger.info("No active jobs. Exiting...")
                            break
                    
                    if consecutive_empty == 1:
                        self.logger.info("No pending jobs. Waiting...")
                    elif consecutive_empty % 10 == 0:
                        # 10번마다 한 번씩 로그
                        self.logger.info(
                            f"Still waiting for jobs... "
                            f"({consecutive_empty} polls, {consecutive_empty * poll_interval}s elapsed)"
                        )
                    
                    await asyncio.sleep(poll_interval)
            except KeyboardInterrupt:
                self.logger.info("Worker stopped by user")
                break
                
            except Exception as e:
                self.logger.error(
                    f"Unexpected error in worker loop: {e}",
                    exc_info=True
                )
                await asyncio.sleep(poll_interval)