from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.routes.contacts import router as contacts_router
from api.routes.device import router as device_router
from api.routes.messages import router as messages_router
from api.routes.testing import router as testing_router
from core.queue_manager import QueueManager
from core.session import SessionManager
from db.repository import FavoriteRepository, MessageRepository
from device.base import AbstractDevice


def build_fastapi_app(
    device:          AbstractDevice,
    session_mgr:     SessionManager,
    queue_mgr:       QueueManager,
    session_factory: async_sessionmaker[AsyncSession],
    msg_repo:        MessageRepository,
    fav_repo:        FavoriteRepository,
) -> FastAPI:
    app = FastAPI(title="Braille Glove API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.device          = device
    app.state.session_mgr     = session_mgr
    app.state.queue_mgr       = queue_mgr
    app.state.session_factory = session_factory
    app.state.msg_repo        = msg_repo
    app.state.fav_repo        = fav_repo

    app.include_router(messages_router, prefix="/api/v1")
    app.include_router(contacts_router, prefix="/api/v1")
    app.include_router(device_router,   prefix="/api/v1")
    app.include_router(testing_router,  prefix="/api/v1")

    return app
