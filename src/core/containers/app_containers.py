from dependency_injector import containers, providers
from motor.motor_asyncio import AsyncIOMotorClient
from core.config.settings import settings
from core.llm.openai_client import OpenAIClient


class AppContainer(containers.DeclarativeContainer):

    mongo_client = providers.Singleton(
        AsyncIOMotorClient,
        settings.MONGO_URL
    )
    
    llm_client = providers.Singleton(
        OpenAIClient,
        api_key=settings.OPENAI_API_KEY.get_secret_value()
    )

