# src/ingest/sources/github/client.py

from re import S
from github import Github
import base64
from github.Repository import Repository
from github.ContentFile import ContentFile
from typing import Iterable, Optional
from core.logging.logger import get_logger



class GitHubClient:
    """
    Low-level GitHub API wrapper.
    Only responsible for HTTP communication.
    """

    def __init__(self, token: str):
        self.client = Github(token, per_page=50)
        self.logger = get_logger(__name__) 

    def search_repositories(self, query: str) -> Iterable[Repository]:
        """
        Just call GitHub search API
        """
        return self.client.search_repositories(
            query=query,
            sort="stars",
            order="desc",
        )

    def get_readme(self, full_name: str) -> Optional[str]:
        """
        Core API: README 콘텐츠 가져오기
        
        Args: 
            full_name: owner/repo
        Returns:
            README 콘텐츠 (text) or None if not found
        """
        try:
            repo = self.client.get_repo(full_name)
            readme: ContentFile = repo.get_readme()
            content = base64.b64decode(readme.content).decode('utf-8')
            return content
        except Exception as e:
            self.logger.error(f"Failed to get README for {full_name}: {e}")
            return None
