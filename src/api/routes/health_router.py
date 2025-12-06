# src/api/routes/health.py
from fastapi import APIRouter
from dependency_injector.wiring import Provide, inject

from core.containers.app_containers import AppContainer

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
@inject
async def health_check(client=Provide[AppContainer.mongo_client]):
    # 실제 MongoDB ping 테스트
    try:
        await client.admin.command("ping")
        mongo_status = "connected"
    except Exception:
        mongo_status = "disconnected"

    return {
        "status": "ok",
        "mongo": mongo_status
    }
