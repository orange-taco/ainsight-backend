import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from core.logging.logger import get_logger

class ClassifyWorker:
    """README를 읽고 LLM으로 라이브러리 분류"""

    def __init__(self, mongo, llm_client, worker_id: int):
        self.db = mongo["ainsight"]
        self.jobs_col = self.db["github_classify_jobs"]
        self.repos_col = self.db["github_repositories"]
        self.llm = llm_client
        self.worker_id = worker_id
        self.logger = get_logger(__name__)
        self.current_job_id = None
        self.shutdown_requested = False

    async def acquire_job(self) -> Optional[dict]:
        return await self.jobs_col.find_one_and_update(
            {"status": "pending", "$expr": {"$lt": ["$attempts", "$max_attempts"]}},
            {
                "$set": {"status": "running", "started_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)},
                "$inc": {"attempts": 1},
            },
            sort=[("created_at", 1)],
            return_document=True,
        )

    async def cleanup(self):
        if self.current_job_id:
            await self.jobs_col.update_one(
                {"_id": self.current_job_id, "status": "running"},
                {"$set": {"status": "pending", "updated_at": datetime.now(timezone.utc), "attempts": 0}}
            )

    async def process_job(self, job: dict):
        self.current_job_id = job["_id"]
        repo_id = job["repo_id"]
        
        self.logger.info(f"[worker-{self.worker_id}] [Job {self.current_job_id}] Classifying repo_id={repo_id}")

        try:
            # README 가져오기
            repo = await self.repos_col.find_one({"repo_id": repo_id})
            if not repo or not repo.get("enrichment", {}).get("readme_content"):
                raise ValueError("No README content found")

            readme = repo["enrichment"]["readme_content"][:2000]  # 처음 2000자만
            
            # LLM 분류
            result = await self._classify_with_llm(readme)
            
            # 결과 저장
            await self.repos_col.update_one(
                {"repo_id": repo_id},
                {
                    "$set": {
                        "enrichment.ai_classified": True,
                        "classification": result,
                        "enrichment.classified_at": datetime.now(timezone.utc),
                    }
                }
            )
            
            # Job 완료
            await self.jobs_col.update_one(
                {"_id": self.current_job_id},
                {"$set": {"status": "done", "completed_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)}}
            )
            
            self.logger.info(
                f"[worker-{self.worker_id}] [Job {self.current_job_id}] ✅ "
                f"is_library={result['is_library']}, category={result.get('category', 'N/A')}"
            )

        except Exception as e:
            await self._handle_error(job, str(e))

    VALID_CATEGORIES = (
        "web_framework", "data_science", "ml_ai", "cli", "testing",
        "database", "http", "devtools", "auth", "messaging", "cloud",
        "ui", "validation", "logging", "networking", "other",
    )

    async def _classify_with_llm(self, readme: str) -> dict:
        """LLM 호출하여 분류"""
        categories = ", ".join(f'"{c}"' for c in self.VALID_CATEGORIES)
        prompt = f"""You are a classifier. Determine if this GitHub repository is a reusable library/package or an end-user application.

README:
{readme}

Respond with ONLY valid JSON, no other text. Follow this exact format:

{{
  "is_library": true,
  "category": "web_framework",
  "confidence": 0.85,
  "reason": "This is a reusable HTTP client library"
}}

Rules:
- "is_library": must be true or false
- "category": one of {categories}
- "confidence": number between 0.0 and 1.0
- "reason": one sentence explanation
- Do NOT include any text outside the JSON object"""

        response = await self.llm.generate(prompt)
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from LLM: {e}") from e
        for key in ("is_library", "confidence", "reason", "category"):
            if key not in data:
                raise ValueError(f"LLM response missing key: {key}")
        if data["category"] not in self.VALID_CATEGORIES:
            data["category"] = "other"
        return data

    async def _handle_error(self, job: dict, error_msg: str):
        self.logger.error(f"[worker-{self.worker_id}] [Job {self.current_job_id}] Error: {error_msg}")
        
        attempts = job.get("attempts", 0)
        max_attempts = job.get("max_attempts", 3)
        status = "failed" if attempts >= max_attempts else "pending"
        
        await self.jobs_col.update_one(
            {"_id": self.current_job_id},
            {
                "$set": {
                    "status": status,
                    "completed_at": datetime.now(timezone.utc) if status == "failed" else None,
                    "updated_at": datetime.now(timezone.utc),
                    "error_message": error_msg,
                }
            }
        )
        self.current_job_id = None

    async def run(self, poll_interval: int = 10, auto_exit: bool = True, startup_wait: int = 5):
        self.logger.info(f"Worker-{self.worker_id} started. Polling for jobs...")
        
        consecutive_empty = 0
        startup_grace_period = startup_wait

        try:
            while not self.shutdown_requested:
                job = await self.acquire_job()
                
                if job:
                    consecutive_empty = 0
                    startup_grace_period = 0
                    await self.process_job(job)
                else:
                    consecutive_empty += 1
                    if auto_exit and startup_grace_period <= 0:
                        active_count = await self.jobs_col.count_documents({"status": {"$in": ["pending", "running"]}})
                        if active_count == 0:
                            self.logger.info(f"[worker-{self.worker_id}] No active jobs. Exiting...")
                            break
                    
                    if startup_grace_period > 0:
                        startup_grace_period -= 1
                    
                    for _ in range(poll_interval):
                        if self.shutdown_requested:
                            break
                        await asyncio.sleep(1)
                    
        except KeyboardInterrupt:
            self.logger.info("KeyboardInterrupt received")
        finally:
            self.logger.info("Running cleanup...")
            await self.cleanup()
