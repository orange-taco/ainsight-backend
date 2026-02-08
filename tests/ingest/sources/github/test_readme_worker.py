import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId

import pytest

from ingest.sources.github.readme.readme_worker import ReadmeWorker


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
        "full_name": "owner/repo",
        "attempts": 1,
        "max_attempts": 3,
        "status": "running",
    }
    base.update(overrides)
    return base


class TestCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_skips_when_no_current_job(self):
        worker = ReadmeWorker(make_mongo_mock(), token="t", worker_id=1, total_workers=2)
        worker.current_job_id = None
        await worker.cleanup()
        worker.jobs_col.update_one.assert_not_called()

    @pytest.mark.asyncio
    async def test_current_job_id_cleared_after_success(self):
        worker = ReadmeWorker(make_mongo_mock(), token="t", worker_id=1, total_workers=2)
        worker.jobs_col = AsyncMock()
        worker.repos_col = AsyncMock()

        with patch("asyncio.to_thread", new_callable=lambda: AsyncMock) as mock_tt:
            mock_tt.return_value = "# Hello README"
            await worker.process_job(make_job())

        assert worker.current_job_id is None


class TestSignalHandler:
    def test_signal_sets_shutdown(self):
        from ingest.sources.github.readme import readme_main
        worker = MagicMock(shutdown_requested=False)
        readme_main.worker_instance = worker
        readme_main.signal_handler(signal.SIGTERM, None)
        assert worker.shutdown_requested is True


class TestGracefulShutdown:
    @pytest.mark.asyncio
    async def test_exits_on_shutdown(self):
        worker = ReadmeWorker(make_mongo_mock(), token="t", worker_id=1, total_workers=2)
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
    async def test_readme_uses_to_thread(self):
        worker = ReadmeWorker(make_mongo_mock(), token="t", worker_id=1, total_workers=2)
        worker.jobs_col = AsyncMock()
        worker.repos_col = AsyncMock()

        with patch("asyncio.to_thread", new_callable=lambda: AsyncMock) as mock_tt:
            mock_tt.return_value = "# README"
            await worker.process_job(make_job())

        mock_tt.assert_called_once_with(worker.client.get_readme, "owner/repo")
