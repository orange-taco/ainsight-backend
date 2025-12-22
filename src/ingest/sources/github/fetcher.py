# src/ingest/sources/github/fetcher.py

from datetime import datetime
from pymongo.errors import BulkWriteError

from ingest.sources.github.client import GitHubClient
from ingest.sources.github.filters import (
    is_valid_repo,
    is_meaningful_readme,
)
from core.logging.logger import get_logger


class GitHubIngestor:
    """
    GitHub repository ingest use-case
    """

    PIPELINE_VERSION = "github_ingest_v1"

    def __init__(self, mongo, token: str):
        self.client = GitHubClient(token)
        self.collection = mongo["ainsight"]["github_repo_raw"]
        self.logger = get_logger(__name__)

    async def run(self, query: str, limit: int = 50, min_stars: int = 20, min_size: int = 50, min_pushed_at: int = 180):
        """
        1) search
        2) secondary filter
        3) readme filter
        4) store
        """
        self.logger.info(f"Running GitHub ingestion for query: {query}")
        documents = []

        repos = self.client.search_repositories(query)

        for idx, repo in enumerate(repos):
            if idx >= limit:
                break

            # 2차 필터
            if not is_valid_repo(repo, min_stars=min_stars, min_size=min_size, min_pushed_at=min_pushed_at):
                continue

            # README 필터
            readme_object = self.client.get_readme(repo)
            if not readme_object:
                continue

            readme_text = readme_object.decoded_content.decode("utf-8", errors="ignore")
            if not is_meaningful_readme(readme_text):
                continue

            documents.append(self._map_repo(repo=repo, readme_text=readme_text, query=query,))


        self.logger.info(f"Found {len(documents)} repositories to ingest")

        if not documents:
            return 

        try: 
            await self.collection.insert_many(documents, ordered=False)
            self.logger.info(f"Inserted {len(documents)} repositories into MongoDB")
        except BulkWriteError:
            self.logger.info(f"duplicate keys skipped")
            pass

    def _map_repo(self, repo, readme_text: str, query: str) -> dict:
        return {
            "source": "github",
            "external_id": repo.id,
            "full_name": repo.full_name,
            "name": repo.name,
            "owner": repo.owner.login,
            "url": repo.html_url,
            "stars": repo.stargazers_count,
            "forks": repo.forks_count,
            "language": repo.language,
            "activity": {
                "created_at": repo.created_at,
                "updated_at": repo.updated_at,
                "pushed_at": repo.pushed_at,
            },
            "raw": {
                "repo": repo.raw_data,
                "readme": {
                    "content": readme_text,
                    "length": len(readme_text),
                },
            },
            "ingest_meta": {
                "ingested_at": datetime.utcnow(),
                "query": query,
                "pipeline_version": self.PIPELINE_VERSION,
            },
        }
