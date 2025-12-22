# src/ingest/sources/github/client.py

from github import Github
from github.Repository import Repository
from github.ContentFile import ContentFile
from typing import Iterable


class GitHubClient:
    """
    Low-level GitHub API wrapper.
    Only responsible for HTTP communication.
    """

    def __init__(self, token: str):
        self.client = Github(token, per_page=50)

    def search_repositories(self, query: str) -> Iterable[Repository]:
        """
        Just call GitHub search API
        """
        return self.client.search_repositories(
            query=query,
            sort="stars",
            order="desc",
        )

    def get_readme(self, repo: Repository) -> ContentFile | None:
        """
        Fetch README if exists
        """
        try:
            return repo.get_readme()
        except Exception:
            return None
