import pytest

from ble.protocol import ButtonEvent, ButtonType, EventType
from braille.constants import CELL_END_OF_MESSAGE, CELL_SEPARATOR
from core.session import GloveMode


def _tap(button: ButtonType, event: EventType = EventType.SINGLE_TAP) -> ButtonEvent:
    return ButtonEvent(button=button, event=event)


async def test_switch_to_compose_sends_separator_cue(session_manager, sim_device):
    sim_device.clear_haptic_log()
    await session_manager.handle_button_event(_tap(ButtonType.NEXT, EventType.DOUBLE_TAP))
    masks = [m for m, _ in sim_device.haptic_log]
    assert masks.count(CELL_SEPARATOR) == 2


async def test_switch_to_read_sends_end_of_message_cue(session_manager, sim_device):
    await session_manager.handle_button_event(_tap(ButtonType.NEXT, EventType.DOUBLE_TAP))
    sim_device.clear_haptic_log()
    await session_manager.handle_button_event(_tap(ButtonType.NEXT, EventType.DOUBLE_TAP))
    masks = [m for m, _ in sim_device.haptic_log]
    assert CELL_END_OF_MESSAGE in masks


async def test_compose_state_cleared_on_cancel(session_manager):
    await session_manager.handle_button_event(_tap(ButtonType.NEXT, EventType.DOUBLE_TAP))
    from braille.charset import GRADE1_MAP
    from ble.protocol import ButtonEvent
    await session_manager.handle_button_event(
        ButtonEvent(ButtonType.BRAILLE, EventType.SINGLE_TAP, dot_mask=GRADE1_MAP["a"])
    )
    assert session_manager._compose.typed_text == "a"
    await session_manager.handle_button_event(_tap(ButtonType.NEXT, EventType.DOUBLE_TAP))
    assert session_manager._compose.typed_text == ""


async def test_favorite_slot_wraps_forward(
    session_manager, db_session_factory, fav_repo
):
    from db.models import Favorite
    async with db_session_factory() as session:
        async with session.begin():
            await fav_repo.upsert(session, Favorite(slot=0, name="A", telegram_id="1"))
            await fav_repo.upsert(session, Favorite(slot=1, name="B", telegram_id="2"))

    await session_manager.handle_button_event(_tap(ButtonType.NEXT, EventType.DOUBLE_TAP))
    assert session_manager._compose.favorite_slot == 0
    await session_manager.handle_button_event(_tap(ButtonType.NEXT))
    assert session_manager._compose.favorite_slot == 1
    await session_manager.handle_button_event(_tap(ButtonType.NEXT))
    assert session_manager._compose.favorite_slot == 0  # wraps


async def test_favorite_slot_wraps_backward(
    session_manager, db_session_factory, fav_repo
):
    from db.models import Favorite
    async with db_session_factory() as session:
        async with session.begin():
            await fav_repo.upsert(session, Favorite(slot=0, name="A", telegram_id="1"))
            await fav_repo.upsert(session, Favorite(slot=1, name="B", telegram_id="2"))

    await session_manager.handle_button_event(_tap(ButtonType.NEXT, EventType.DOUBLE_TAP))
    await session_manager.handle_button_event(_tap(ButtonType.PREV))
    assert session_manager._compose.favorite_slot == 1  # wraps backward


async def test_no_favorites_enter_is_noop(session_manager, mock_messaging):
    await session_manager.handle_button_event(_tap(ButtonType.NEXT, EventType.DOUBLE_TAP))
    from braille.charset import GRADE1_MAP
    from ble.protocol import ButtonEvent
    await session_manager.handle_button_event(
        ButtonEvent(ButtonType.BRAILLE, EventType.SINGLE_TAP, dot_mask=GRADE1_MAP["h"])
    )
    await session_manager.handle_button_event(_tap(ButtonType.ENTER))
    assert mock_messaging.sent == []


async def test_mode_persists_through_braille_input(session_manager):
    await session_manager.handle_button_event(_tap(ButtonType.NEXT, EventType.DOUBLE_TAP))
    from braille.charset import GRADE1_MAP
    from ble.protocol import ButtonEvent
    for ch in "abc":
        await session_manager.handle_button_event(
            ButtonEvent(ButtonType.BRAILLE, EventType.SINGLE_TAP, dot_mask=GRADE1_MAP[ch])
        )
    assert session_manager.mode == GloveMode.COMPOSE
