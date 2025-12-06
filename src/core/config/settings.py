# src/web/config/settings.py

from pydantic_settings import BaseSettings
from pydantic import Field


class AppSettings(BaseSettings):
    APP_NAME: str = "GitChat"
    DEBUG: bool = True

    HOST: str = "0.0.0.0"
    PORT: int = 8000


    MONGO_URL: str

    class Config:
        # docker-compose env_file 환경변수 사용 중
        pass


settings = AppSettings()
