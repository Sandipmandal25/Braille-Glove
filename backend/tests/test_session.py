import time

import pytest

from ble.protocol import ButtonEvent, ButtonType, EventType
from braille.constants import CELL_CONNECT_CUE, CELL_END_OF_MESSAGE
from core.session import GloveMode
from db.models import Favorite
from messaging.base import IncomingMessage


def _tap(button: ButtonType, event: EventType = EventType.SINGLE_TAP) -> ButtonEvent:
    return ButtonEvent(button=button, event=event)


def _braille(dot_mask: int) -> ButtonEvent:
    return ButtonEvent(button=ButtonType.BRAILLE, event=EventType.SINGLE_TAP, dot_mask=dot_mask)


async def test_initial_mode_is_read(session_manager):
    assert session_manager.mode == GloveMode.READ


async def test_connect_sends_cue(session_manager, sim_device):
    assert any(mask == CELL_CONNECT_CUE for mask, _ in sim_device.haptic_log)


async def test_double_tap_next_enters_compose(session_manager, sim_device):
    sim_device.clear_haptic_log()
    await session_manager.handle_button_event(_tap(ButtonType.NEXT, EventType.DOUBLE_TAP))
    assert session_manager.mode == GloveMode.COMPOSE


async def test_double_tap_next_in_compose_returns_read(session_manager):
    await session_manager.handle_button_event(_tap(ButtonType.NEXT, EventType.DOUBLE_TAP))
    await session_manager.handle_button_event(_tap(ButtonType.NEXT, EventType.DOUBLE_TAP))
    assert session_manager.mode == GloveMode.READ


async def test_braille_tap_appends_to_typed_text(session_manager):
    await session_manager.handle_button_event(_tap(ButtonType.NEXT, EventType.DOUBLE_TAP))
    from braille.charset import GRADE1_MAP
    await session_manager.handle_button_event(_braille(GRADE1_MAP["a"]))
    assert session_manager._compose.typed_text == "a"


async def test_backspace_removes_last_char(session_manager):
    await session_manager.handle_button_event(_tap(ButtonType.NEXT, EventType.DOUBLE_TAP))
    from braille.charset import GRADE1_MAP
    await session_manager.handle_button_event(_braille(GRADE1_MAP["a"]))
    await session_manager.handle_button_event(_braille(GRADE1_MAP["b"]))
    await session_manager.handle_button_event(_tap(ButtonType.PREV, EventType.DOUBLE_TAP))
    assert session_manager._compose.typed_text == "a"


async def test_enter_with_empty_buffer_is_noop(
    session_manager, mock_messaging, db_session_factory, fav_repo
):
    async with db_session_factory() as session:
        async with session.begin():
            await fav_repo.upsert(
                session, Favorite(slot=0, name="Alice", telegram_id="111")
            )
    await session_manager.handle_button_event(_tap(ButtonType.NEXT, EventType.DOUBLE_TAP))
    await session_manager.handle_button_event(_tap(ButtonType.ENTER))
    assert mock_messaging.sent == []


async def test_enter_sends_message(
    session_manager, mock_messaging, db_session_factory, fav_repo
):
    async with db_session_factory() as session:
        async with session.begin():
            await fav_repo.upsert(
                session, Favorite(slot=0, name="Alice", telegram_id="111")
            )
    await session_manager.handle_button_event(_tap(ButtonType.NEXT, EventType.DOUBLE_TAP))
    from braille.charset import GRADE1_MAP
    await session_manager.handle_button_event(_braille(GRADE1_MAP["h"]))
    await session_manager.handle_button_event(_braille(GRADE1_MAP["i"]))
    await session_manager.handle_button_event(_tap(ButtonType.ENTER))
    assert len(mock_messaging.sent) == 1
    assert mock_messaging.sent[0].text == "hi"
    assert mock_messaging.sent[0].recipient_id == "111"


async def test_message_played_on_connect(queue_manager, sim_device, mock_messaging, fav_repo, db_session_factory):
    from core.session import SessionManager
    from messaging.base import IncomingMessage

    await queue_manager.enqueue_from_external(
        IncomingMessage("ext1", "u1", "Bob", "hello", time.time())
    )
    sm = SessionManager(sim_device, queue_manager, mock_messaging, fav_repo, db_session_factory)
    sim_device.register_connect_callback(sm.on_device_connected)
    sim_device.clear_haptic_log()
    await sim_device.connect()

    from braille.codec import encode_text
    expected_cells = encode_text("hello")
    played_masks = [mask for mask, _ in sim_device.haptic_log]
    for cell in expected_cells:
        assert cell in played_masks
