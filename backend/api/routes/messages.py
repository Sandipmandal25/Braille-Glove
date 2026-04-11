from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from api.schemas import MessageListResponse, MessageResponse
from db.repository import MessageRepository
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

router = APIRouter(prefix="/messages", tags=["messages"])


def _get_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return request.app.state.session_factory


def _get_msg_repo(request: Request) -> MessageRepository:
    return request.app.state.msg_repo


Factory = Annotated[async_sessionmaker[AsyncSession], Depends(_get_factory)]
MsgRepo = Annotated[MessageRepository, Depends(_get_msg_repo)]


def _to_response(msg) -> MessageResponse:
    return MessageResponse(
        id=msg.id,
        external_id=msg.external_id,
        sender_id=msg.sender_id,
        sender_name=msg.sender_name,
        text=msg.text,
        status=msg.status,
        timestamp=msg.timestamp,
    )


@router.get("", response_model=MessageListResponse)
async def list_messages(
    factory:  Factory,
    msg_repo: MsgRepo,
    status:   str | None = None,
    limit:    int        = 100,
    offset:   int        = 0,
) -> MessageListResponse:
    async with factory() as session:
        if status == "unread":
            items = await msg_repo.list_unread(session)
            total = len(items)
        elif status == "read":
            items = await msg_repo.list_read(session)
            total = len(items)
        else:
            items = await msg_repo.list_all(session, limit=limit, offset=offset)
            total = await msg_repo.count_all(session)
    return MessageListResponse(items=[_to_response(m) for m in items], total=total)


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: int,
    factory:    Factory,
    msg_repo:   MsgRepo,
) -> MessageResponse:
    async with factory() as session:
        msg = await msg_repo.get_by_id(session, message_id)
    if msg is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return _to_response(msg)


@router.post("/{message_id}/read", response_model=MessageResponse)
async def mark_read(
    message_id: int,
    factory:    Factory,
    msg_repo:   MsgRepo,
) -> MessageResponse:
    async with factory() as session:
        async with session.begin():
            msg = await msg_repo.get_by_id(session, message_id)
            if msg is None:
                raise HTTPException(status_code=404, detail="Message not found")
            await msg_repo.mark_read(session, message_id)
            msg.status = "read"
    return _to_response(msg)


@router.delete("/{message_id}", status_code=204)
async def delete_message(
    message_id: int,
    factory:    Factory,
    msg_repo:   MsgRepo,
) -> None:
    async with factory() as session:
        async with session.begin():
            deleted = await msg_repo.delete_by_id(session, message_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Message not found")
