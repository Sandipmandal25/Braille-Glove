import time
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ble.protocol import ButtonEvent, ButtonType, EventType
from core.queue_manager import QueueManager
from core.session import SessionManager
from messaging.base import IncomingMessage

router = APIRouter(prefix="/test", tags=["testing"])


class InjectMessageRequest(BaseModel):
    sender_name: str = "Test User"
    sender_id: str   = "99999"
    text: str


class ButtonEventRequest(BaseModel):
    button:   str       # PREV | NEXT | ENTER | BRAILLE
    event:    str       # SINGLE | DOUBLE
    dot_mask: int | None = None  # only for BRAILLE button


def _get_queue_mgr(request: Request) -> QueueManager:
    return request.app.state.queue_mgr


def _get_session_mgr(request: Request) -> SessionManager:
    return request.app.state.session_mgr


QueueMgr   = Annotated[QueueManager,   Depends(_get_queue_mgr)]
SessionMgr = Annotated[SessionManager, Depends(_get_session_mgr)]


@router.post("/inject", status_code=201)
async def inject_message(body: InjectMessageRequest, queue_mgr: QueueMgr) -> dict:
    """Inject a fake incoming message — for testing without a real Telegram message."""
    msg = IncomingMessage(
        external_id=str(uuid.uuid4()),
        sender_id=body.sender_id,
        sender_name=body.sender_name,
        text=body.text,
        timestamp=time.time(),
    )
    await queue_mgr.enqueue_from_external(msg)
    return {"status": "injected"}


@router.post("/select_contact/{slot}", status_code=200)
async def select_contact(slot: int, session_mgr: SessionMgr) -> dict:
    """Directly jump to a contact slot in COMPOSE mode (skips PREV/NEXT cycling)."""
    session_mgr._compose.favorite_slot = slot
    return {"status": "ok", "slot": slot, "mode": session_mgr.mode.name}


@router.post("/button", status_code=200)
async def inject_button(body: ButtonEventRequest, session_mgr: SessionMgr) -> dict:
    """Simulate a glove button press — drives the session state machine directly."""
    btn_map   = {"PREV": ButtonType.PREV, "NEXT": ButtonType.NEXT,
                 "ENTER": ButtonType.ENTER, "BRAILLE": ButtonType.BRAILLE}
    event_map = {"SINGLE": EventType.SINGLE_TAP, "DOUBLE": EventType.DOUBLE_TAP}

    button = btn_map.get(body.button.upper())
    event  = event_map.get(body.event.upper())
    if button is None or event is None:
        return {"status": "error", "detail": "unknown button or event type"}

    btn_event = ButtonEvent(button=button, event=event, dot_mask=body.dot_mask)
    await session_mgr.handle_button_event(btn_event)
    return {"status": "ok", "mode": session_mgr.mode.name}
