import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.schemas import DeviceStatusResponse
from db.repository import MessageRepository
from device.base import AbstractDevice

router = APIRouter(prefix="/device", tags=["device"])


def _get_device(request: Request) -> AbstractDevice:
    return request.app.state.device


def _get_session_mgr(request: Request):
    return request.app.state.session_mgr


def _get_queue_mgr(request: Request):
    return request.app.state.queue_mgr


def _get_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return request.app.state.session_factory


def _get_msg_repo(request: Request) -> MessageRepository:
    return request.app.state.msg_repo


Device     = Annotated[AbstractDevice, Depends(_get_device)]
SessionMgr = Annotated[object, Depends(_get_session_mgr)]
QueueMgr   = Annotated[object, Depends(_get_queue_mgr)]
Factory    = Annotated[async_sessionmaker[AsyncSession], Depends(_get_factory)]
MsgRepo    = Annotated[MessageRepository, Depends(_get_msg_repo)]


@router.get("/status", response_model=DeviceStatusResponse)
async def device_status(
    device:    Device,
    session_mgr: SessionMgr,
    queue_mgr: QueueMgr,
    factory:   Factory,
    msg_repo:  MsgRepo,
) -> DeviceStatusResponse:
    async with factory() as session:
        unread = await msg_repo.count_unread(session)
    return DeviceStatusResponse(
        connected=device.is_connected,
        mode=session_mgr.mode.name,
        queue_length=queue_mgr.queue_length(),
        cursor_position=queue_mgr.cursor_position(),
        unread_count=unread,
        compose_slot=session_mgr.compose_slot,
        compose_text=session_mgr.compose_text,
    )


@router.post("/connect", status_code=202)
async def connect_device(device: Device) -> dict:
    asyncio.ensure_future(device.connect())
    return {"status": "connecting"}


@router.post("/disconnect", status_code=202)
async def disconnect_device(device: Device) -> dict:
    asyncio.ensure_future(device.disconnect())
    return {"status": "disconnecting"}
