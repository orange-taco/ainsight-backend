# src/core/containers/app_container.py

from dependency_injector import containers, providers
from motor.motor_asyncio import AsyncIOMotorClient
from core.config.settings import settings


class AppContainer(containers.DeclarativeContainer):

    wiring_config = containers.WiringConfiguration(
        modules=["api.routes.health_router"]
    )

    mongo_client = providers.Singleton(
        AsyncIOMotorClient,
        settings.MONGO_URL
    )

