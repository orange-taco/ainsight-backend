# src/ingest/sources/github/fetcher.py

from datetime import datetime
from pymongo.errors import BulkWriteError

from ingest.sources.github.client import GitHubClient
from ingest.sources.github.filters import (
    is_valid_repo,
)
from core.logging.logger import get_logger
from ingest.mappers.github_repo_mapper import map_repo


class GitHubIngestor:
    """
    GitHub repository ingest use-case
    """

    def __init__(self, mongo, token: str, pipeline_version: str):
        self.client = GitHubClient(token)
        self.collection = mongo["ainsight"]["github_repo_raw"]
        self.logger = get_logger(__name__)
        self.pipeline_version = pipeline_version


    async def run(self, query: str, bucket: str, min_size: int = 50, min_pushed_at: int = 30):
        """
        1) search
        2) secondary filter
        3) readme filter
        4) store
        """
        self.logger.info(f"Running GitHub ingestion for query: {query}")
        documents = []

        repos = self.client.search_repositories(query)
        self.logger.info(f"Found {repos.totalCount} repositories to ingest")
        for idx, repo in enumerate(repos):
            # 2차 필터
            if not is_valid_repo(repo, min_size=min_size, min_pushed_at=min_pushed_at):
                continue

            documents.append(map_repo(repo=repo, query=query, bucket=bucket, pipeline_version=self.pipeline_version))


        self.logger.info(f"filtered {len(documents)} repositories to ingest")

        if not documents:
            return 

        try: 
            await self.collection.insert_many(documents, ordered=False)
            self.logger.info(f"Inserted {len(documents)} repositories into MongoDB")
        except BulkWriteError:
            self.logger.info(f"duplicate keys skipped")
            pass

