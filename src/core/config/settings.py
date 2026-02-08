from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr
from typing import List, Dict


class AppSettings(BaseSettings):
    APP_NAME: str = "Ainsight"
    DEBUG: bool = True

    HOST: str = "0.0.0.0"
    PORT: int = 8000


    MONGO_URL: str
    MONGO_URI: str
    MONGO_DB_NAME: str

    # ===== INGEST =====
    WORKER_ID: int = 1
    TOTAL_WORKERS: int = 1
     
    # ===== Reddit =====
    # REDDIT_CLIENT_ID: str
    # REDDIT_CLIENT_SECRET: str
    # REDDIT_SUBREDDITS: List[str]

    # ===== GitHub =====
    GITHUB_TOKEN_1: str
    GITHUB_TOKEN_2: str
    GITHUB_INGEST_PIPELINE_VERSION: str = "github_ingest_v1"

    # ===== OpenAI =====
    OPENAI_API_KEY: SecretStr

    # Job Configuration
    GITHUB_INGEST_BUCKET_PREFIX: str = "ml_repos"
    GITHUB_INGEST_QUERY_TEMPLATE: str = "created:{from_date}..{to_date} stars:>20"
    GITHUB_INGEST_START_DATE: str = "2022-01-01"
    GITHUB_INGEST_END_DATE: str = "2024-12-31"
    GITHUB_INGEST_WINDOW_DAYS: int = 3
    def get_github_token(self) -> str:
        """워커 ID에 맞는 토큰 반환"""
        if self.WORKER_ID == 1:
            return self.GITHUB_TOKEN_1
        elif self.WORKER_ID == 2:
            return self.GITHUB_TOKEN_2
        return self.GITHUB_TOKEN_1  # fallback
    class Config:
        extra = "ignore"


settings = AppSettings()
