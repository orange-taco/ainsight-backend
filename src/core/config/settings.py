from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class AppSettings(BaseSettings):
    APP_NAME: str = "Ainsight"
    DEBUG: bool = True

    HOST: str = "0.0.0.0"
    PORT: int = 8000


    MONGO_URL: str

    # REDDIT_CLIENT_ID: str
    # REDDIT_CLIENT_SECRET: str
    # REDDIT_SUBREDDITS: List[str]

    class Config:
        # docker-compose env_file 환경변수 사용 중
        pass


settings = AppSettings()
