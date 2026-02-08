import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId

import pytest

from ingest.sources.github.search.search_worker import GitHubJobWorker


def make_mongo_mock():
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=AsyncMock())
    mongo = MagicMock()
    mongo.__getitem__ = MagicMock(return_value=db)
    return mongo


def make_job(**overrides):
    base = {
        "_id": ObjectId(),
        "bucket": "test",
        "query_template": "created:{from_date}..{to_date} stars:>20",
        "window": {"from": "2024-01-01", "to": "2024-01-03"},
        "attempts": 1,
        "max_attempts": 3,
        "status": "running",
    }
    base.update(overrides)
    return base


class TestCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_skips_when_no_current_job(self):
        worker = GitHubJobWorker(make_mongo_mock(), token="t", worker_id=1, pipeline_version="v1")
        worker.current_job_id = None
        await worker.cleanup()
        worker.jobs_col.update_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_restores_running_job(self):
        worker = GitHubJobWorker(make_mongo_mock(), token="t", worker_id=1, pipeline_version="v1")
        worker.jobs_col = AsyncMock()
        worker.jobs_col.update_one.return_value = MagicMock(modified_count=1)
        job_id = ObjectId()
        worker.current_job_id = job_id
        await worker.cleanup()
        call_args = worker.jobs_col.update_one.call_args
        assert call_args[0][0] == {"_id": job_id, "status": "running"}
        assert call_args[0][1]["$set"]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_current_job_id_cleared_after_success(self):
        worker = GitHubJobWorker(make_mongo_mock(), token="t", worker_id=1, pipeline_version="v1")
        worker.jobs_col = AsyncMock()
        worker.repos_col = AsyncMock()
        mock_repos = MagicMock(totalCount=0)

        with patch("asyncio.to_thread", new_callable=lambda: AsyncMock) as mock_tt:
            mock_tt.side_effect = [mock_repos, []]
            await worker.process_job(make_job())

        assert worker.current_job_id is None


class TestSignalHandler:
    def test_signal_sets_shutdown(self):
        from ingest.sources.github.search import search_main
        worker = MagicMock(shutdown_requested=False)
        search_main.worker_instance = worker
        search_main.signal_handler(signal.SIGTERM, None)
        assert worker.shutdown_requested is True


class TestGracefulShutdown:
    @pytest.mark.asyncio
    async def test_exits_on_shutdown(self):
        worker = GitHubJobWorker(make_mongo_mock(), token="t", worker_id=1, pipeline_version="v1")
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


class TestAsyncioToThread:
    @pytest.mark.asyncio
    async def test_search_uses_to_thread(self):
        worker = GitHubJobWorker(make_mongo_mock(), token="t", worker_id=1, pipeline_version="v1")
        worker.jobs_col = AsyncMock()
        worker.repos_col = AsyncMock()
        mock_repos = MagicMock(totalCount=0)

        with patch("asyncio.to_thread", new_callable=lambda: AsyncMock) as mock_tt:
            mock_tt.side_effect = [mock_repos, []]
            await worker.process_job(make_job())

        assert mock_tt.call_count == 2
        assert mock_tt.call_args_list[0][0][0] == worker.client.search_repositories
        assert mock_tt.call_args_list[1][0][0] == list
