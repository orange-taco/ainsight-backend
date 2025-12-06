# src/api/main.py

from fastapi import FastAPI
from contextlib import asynccontextmanager

from core.containers.app_containers import AppContainer
from api.routes.health_router import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    container: AppContainer = app.container

    mongo_client = container.mongo_client()
    print("Mongo Connected")

    yield

    mongo_client.close()
    print("Mongo Disconnected")


def create_app() -> FastAPI:
    container = AppContainer()

    app = FastAPI(
        title="GitChat",
        lifespan=lifespan
    )

    # FastAPI 앱에 컨테이너 연결
    app.container = container

    # 라우터 등록
    app.include_router(health_router)

    return app


app = create_app()
