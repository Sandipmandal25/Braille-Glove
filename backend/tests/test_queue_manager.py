import time

import pytest

from messaging.base import IncomingMessage


def _make_incoming(n: int) -> IncomingMessage:
    return IncomingMessage(
        external_id=str(n),
        sender_id="user1",
        sender_name="Alice",
        text=f"message {n}",
        timestamp=time.time() + n,
    )


async def test_empty_queue_after_load(queue_manager):
    await queue_manager.load_unread()
    assert queue_manager.queue_length() == 0
    assert await queue_manager.current_message() is None


async def test_enqueue_and_load(queue_manager):
    await queue_manager.enqueue_from_external(_make_incoming(1))
    assert queue_manager.queue_length() == 1
    msg = await queue_manager.current_message()
    assert msg is not None
    assert msg.text == "message 1"


async def test_advance_moves_cursor(queue_manager):
    for i in range(3):
        await queue_manager.enqueue_from_external(_make_incoming(i))
    assert queue_manager.cursor_position() == 0
    await queue_manager.advance()
    assert queue_manager.cursor_position() == 1


async def test_advance_at_end_does_not_overflow(queue_manager):
    await queue_manager.enqueue_from_external(_make_incoming(1))
    await queue_manager.advance()
    await queue_manager.advance()
    assert queue_manager.cursor_position() == 0


async def test_retreat_at_start_stays(queue_manager):
    await queue_manager.enqueue_from_external(_make_incoming(1))
    await queue_manager.retreat()
    assert queue_manager.cursor_position() == 0


async def test_retreat_moves_cursor_back(queue_manager):
    for i in range(3):
        await queue_manager.enqueue_from_external(_make_incoming(i))
    await queue_manager.advance()
    await queue_manager.advance()
    assert queue_manager.cursor_position() == 2
    await queue_manager.retreat()
    assert queue_manager.cursor_position() == 1


async def test_mark_current_read_removes_from_queue(queue_manager):
    await queue_manager.enqueue_from_external(_make_incoming(1))
    await queue_manager.mark_current_read()
    assert queue_manager.queue_length() == 0


async def test_jump_to_oldest_resets_cursor(queue_manager):
    for i in range(3):
        await queue_manager.enqueue_from_external(_make_incoming(i))
    await queue_manager.advance()
    await queue_manager.advance()
    await queue_manager.jump_to_oldest_unread()
    assert queue_manager.cursor_position() == 0


async def test_duplicate_external_id_ignored(queue_manager):
    msg = _make_incoming(1)
    await queue_manager.enqueue_from_external(msg)
    await queue_manager.enqueue_from_external(msg)
    assert queue_manager.queue_length() == 1
