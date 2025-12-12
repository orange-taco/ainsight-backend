from dependency_injector import containers, providers
from motor.motor_asyncio import AsyncIOMotorClient
from core.config.settings import settings


class AppContainer(containers.DeclarativeContainer):

    mongo_client = providers.Singleton(
        AsyncIOMotorClient,
        settings.MONGO_URL
    )

