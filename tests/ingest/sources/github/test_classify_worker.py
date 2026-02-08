import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId

import pytest

from ingest.sources.github.classify.classify_worker import ClassifyWorker


def make_mongo_mock():
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=AsyncMock())
    mongo = MagicMock()
    mongo.__getitem__ = MagicMock(return_value=db)
    return mongo


def make_job(**overrides):
    base = {
        "_id": ObjectId(),
        "repo_id": 12345,
        "attempts": 1,
        "max_attempts": 3,
        "status": "running",
    }
    base.update(overrides)
    return base


VALID_LLM_RESPONSE = '{"is_library": true, "category": "web_framework", "confidence": 0.9, "reason": "test"}'

REPO_WITH_README = {
    "repo_id": 12345,
    "enrichment": {"readme_content": "# Test lib"},
}


def make_worker(llm_response=VALID_LLM_RESPONSE):
    llm = AsyncMock()
    llm.generate.return_value = llm_response
    worker = ClassifyWorker(make_mongo_mock(), llm_client=llm, worker_id=1)
    worker.jobs_col = AsyncMock()
    worker.repos_col = AsyncMock()
    worker.repos_col.find_one.return_value = REPO_WITH_README
    return worker


class TestCleanup:
    @pytest.mark.asyncio
    async def test_current_job_id_cleared_after_success(self):
        worker = make_worker()
        await worker.process_job(make_job())
        assert worker.current_job_id is None


class TestSignalHandler:
    def test_signal_sets_shutdown(self):
        from ingest.sources.github.classify import classify_main
        mock_worker = MagicMock(shutdown_requested=False)
        classify_main.worker_instance = mock_worker
        classify_main.signal_handler(signal.SIGTERM, None)
        assert mock_worker.shutdown_requested is True


class TestGracefulShutdown:
    @pytest.mark.asyncio
    async def test_exits_on_shutdown(self):
        worker = ClassifyWorker(make_mongo_mock(), llm_client=AsyncMock(), worker_id=1)
        worker.jobs_col = AsyncMock()
        worker.jobs_col.find_one_and_update.return_value = None
        worker.jobs_col.count_documents.return_value = 1

        original_sleep = asyncio.sleep

        async def fake_sleep(n):
            worker.shutdown_requested = True
            await original_sleep(0)

        with patch("asyncio.sleep", side_effect=fake_sleep):
            await worker.run(poll_interval=1)

        assert worker.shutdown_requested is True


class TestLLMValidation:
    @pytest.mark.asyncio
    async def test_invalid_json_triggers_error_handler(self):
        worker = make_worker(llm_response="not json")
        await worker.process_job(make_job())
        worker.jobs_col.update_one.assert_called()

    @pytest.mark.asyncio
    async def test_missing_key_triggers_error_handler(self):
        worker = make_worker(llm_response='{"is_library": true}')
        await worker.process_job(make_job())
        worker.jobs_col.update_one.assert_called()

    @pytest.mark.asyncio
    async def test_invalid_category_falls_back_to_other(self):
        worker = make_worker(
            llm_response='{"is_library": true, "category": "unknown_cat", "confidence": 0.9, "reason": "test"}'
        )
        await worker.process_job(make_job())
        update_call = worker.repos_col.update_one.call_args
        classification = update_call[0][1]["$set"]["classification"]
        assert classification["category"] == "other"
