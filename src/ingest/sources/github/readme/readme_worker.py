import asyncio
from datetime import datetime, timezone
from typing import Optional
from github import GithubException

from ingest.sources.github.shared.client import GitHubClient
from core.logging.logger import get_logger


class ReadmeWorker:
    """
    github_readme_jobs를 처리하여 README를 수집하는 워커
    """

    def __init__(self, mongo, token: str, worker_id: int, total_workers: int):
        self.db = mongo["ainsight"]
        self.jobs_col = self.db["github_readme_jobs"]
        self.repos_col = self.db["github_repositories"]
        self.client = GitHubClient(token)
        self.worker_id = worker_id  
        self.total_workers = total_workers  
        self.logger = get_logger(__name__)
        self.current_job_id = None  # 현재 처리 중인 job 추적
        self.shutdown_requested = False

        # 진행상황 추적용
        self.processed_count = 0
        self.success_count = 0
        self.no_readme_count = 0
        self.failed_count = 0
        self.start_time = None

    async def cleanup(self):
        """
        Shutdown 시 running job을 pending으로 복구
        """
        if self.current_job_id:
            result = await self.jobs_col.update_one(
                {"_id": self.current_job_id, "status": "running"},
                {
                    "$set": {
                        "status": "pending",
                        "updated_at": datetime.now(timezone.utc),
                    }
                }
            )
            if result.modified_count > 0:
                self.logger.info(
                    f"Restored job {self.current_job_id} to pending on shutdown"
                )

    async def acquire_job(self) -> Optional[dict]:
        """
        pending job을 atomically 가져와 running으로 변경
        """
        job = await self.jobs_col.find_one_and_update(
            {
                "status": "pending",  
                "$expr": {
                    "$and": [
                        {"$lt": ["$attempts", "$max_attempts"]},  # 필드끼리 비교
                        {"$eq": [
                            {"$mod": ["$repo_id", self.total_workers]},
                            self.worker_id - 1
                        ]}
                    ]
                }
            },
            {
                "$set": {
                    "status": "running",
                    "updated_at": datetime.now(timezone.utc),
                },
                "$inc": {"attempts": 1},
            },
            sort=[("created_at", 1)],
            return_document=True,
        )
        
        return job

    async def process_job(self, job: dict):
        """
        단일 job 처리: README 가져오기 → github_repositories 업데이트
        """
        job_id = job["_id"]
        repo_id = job["repo_id"]
        full_name = job["full_name"]
        

        try:
            # GitHub Core API로 README 가져오기
            readme_content = self.client.get_readme(full_name)
            
            if readme_content is None:
                # README 없음
                await self._mark_no_readme(job_id, repo_id, full_name)
                self.no_readme_count += 1
                return
            
            # github_repositories 업데이트
            await self.repos_col.update_one(
                {"repo_id": repo_id},
                {
                    "$set": {
                        "enrichment.readme_fetched": True,
                        "enrichment.readme_content": readme_content,
                        "enrichment.readme_updated_at": datetime.now(timezone.utc),
                    }
                }
            )
            
            # Job 완료 처리
            await self.jobs_col.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "status": "done",
                        "updated_at": datetime.now(timezone.utc),
                        "error_message": None,
                    }
                },
            )

            self.success_count += 1
            
            self.logger.info(
                f"[worker-{self.worker_id}][Job {job_id}] ✅ README fetched for {full_name} "
                f"({len(readme_content)} chars)"
            )
            self.current_job_id = None 

        except GithubException as e:
            await self._handle_github_error(job_id, job, e, full_name)
            self.failed_count += 1

        except Exception as e:
            await self._handle_generic_error(job_id, job, e, full_name)
            self.failed_count += 1

    async def _mark_no_readme(self, job_id, repo_id: int, full_name: str):
        """
        README가 없는 경우 처리
        """
        await self.repos_col.update_one(
            {"repo_id": repo_id},
            {
                "$set": {
                    "enrichment.readme_fetched": True,
                    "enrichment.readme_content": None,
                    "enrichment.readme_updated_at": datetime.now(timezone.utc),
                }
            }
        )
        
        await self.jobs_col.update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": "no_readme",
                    "updated_at": datetime.now(timezone.utc),
                    "error_message": "No README found",
                }
            },
        )
        
        self.logger.info(f"[Job {job_id}] No README for {full_name}")
        self.current_job_id = None 

    async def _handle_github_error(self, job_id, job: dict, error: GithubException, full_name: str):
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
                
                # Job을 pending으로 되돌림
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
                
                # 대기
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds + 2)
                self.current_job_id = None 
                return

        # 그 외 GitHub 에러 (404 등)
        error_msg = f"GitHub API error ({error.status}): {error.data.get('message', str(error))}"
        self.logger.error(f"[worker {self.worker_id} ] [Job {job_id}] {error_msg}")
        await self._mark_job_failed(job_id, job, error_msg)

    async def _handle_generic_error(self, job_id, job: dict, error: Exception, full_name: str):
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
            status = "pending"
            self.logger.warning(f"Job {job_id} failed (attempt {attempts}/{max_attempts}), will retry")

        await self.jobs_col.update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": status,
                    "updated_at": datetime.now(timezone.utc),
                    "error_message": error_message,
                }
            },
        )
        self.current_job_id = None 

    def _log_progress(self):
        """진행상황 로그 출력"""
        if self.start_time is None:
            return
            
        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        rate = self.processed_count / elapsed if elapsed > 0 else 0
        
        self.logger.info(
            f"[Worker {self.worker_id}] Progress: {self.processed_count} jobs processed "
            f"(✅ {self.success_count} success, "
            f"   {self.no_readme_count} no README, "
            f"❌ {self.failed_count} failed) | "
            f"Rate: {rate:.1f} jobs/sec"
        )


    async def run(self, poll_interval: int = 10, auto_exit: bool = True):
        """
        무한 루프로 job 처리
        """
        self.logger.info(f"[Worker {self.worker_id}] README Worker started. Polling for jobs...")
        
        consecutive_empty = 0

        try:
            while not self.shutdown_requested:
                job = await self.acquire_job()
                
                if job:
                    consecutive_empty = 0
                    await self.process_job(job)
                else:
                    consecutive_empty += 1
                    
                    if auto_exit:
                        pending_count = await self.jobs_col.count_documents({
                            "status": {"$in": ["pending", "running"]},
                            "$expr": {
                                "$and": [
                                    {"$lt": ["$attempts", "$max_attempts"]},
                                    {"$eq": [
                                        {"$mod": ["$repo_id", self.total_workers]},
                                        self.worker_id - 1
                                    ]}
                                ]

                            }
                        })
                        if pending_count == 0:
                            self.logger.info(
                                f"[Worker {self.worker_id}] No active jobs in my partition. Exiting..."
                            )
                            break
                    
                    if consecutive_empty == 1:
                        self.logger.info("No pending jobs. Waiting...")
                    elif consecutive_empty % 10 == 0:
                        self.logger.info(
                            f"Still waiting for jobs... "
                            f"({consecutive_empty} polls, {consecutive_empty * poll_interval}s elapsed)"
                        )
                        await asyncio.sleep(poll_interval)

        except asyncio.CancelledError:
            self.logger.info("Worker task cancelled, initiation cleanup...")            
        except KeyboardInterrupt:
            self.logger.info("KeyboardInterrupt received, initiating cleanup...")
        except Exception as e:
            self.logger.error(
                f"Unexpected error in worker loop: {e}",
                exc_info=True
            )
        finally:
            # 항상 cleanup 실행
            self.logger.info("Running cleanup before exit...")
            await self.cleanup()
                   