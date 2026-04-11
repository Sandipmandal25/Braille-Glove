import time

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db.models import Message, MessageStatus
from db.repository import MessageRepository
from messaging.base import IncomingMessage


class QueueManager:
    """
    Manages the ordered list of unread messages the user navigates in READ mode.

    In-memory cursor into a list loaded from DB on glove connect.
    Incoming messages are persisted immediately and appended to the live list
    so they are available without a reconnect.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        msg_repo: MessageRepository,
    ) -> None:
        self._factory   = session_factory
        self._msg_repo  = msg_repo
        self._queue:    list[Message] = []
        self._cursor:   int           = 0

    async def load_unread(self) -> None:
        async with self._factory() as session:
            self._queue = await self._msg_repo.list_unread(session)
        self._cursor = 0

    async def current_message(self) -> Message | None:
        if not self._queue:
            return None
        return self._queue[self._cursor]

    async def advance(self) -> Message | None:
        if self._cursor < len(self._queue) - 1:
            self._cursor += 1
        return await self.current_message()

    async def retreat(self) -> Message | None:
        if self._cursor > 0:
            self._cursor -= 1
        return await self.current_message()

    async def jump_to_oldest_unread(self) -> Message | None:
        self._cursor = 0
        return await self.current_message()

    async def mark_current_read(self) -> None:
        msg = await self.current_message()
        if msg is None:
            return
        async with self._factory() as session:
            async with session.begin():
                await self._msg_repo.mark_read(session, msg.id)
        self._queue.pop(self._cursor)
        if self._cursor >= len(self._queue) and self._cursor > 0:
            self._cursor -= 1

    async def enqueue_from_external(self, incoming: IncomingMessage) -> None:
        """Persist a new incoming message and append it to the live queue."""
        async with self._factory() as session:
            async with session.begin():
                if await self._msg_repo.get_by_external_id(session, incoming.external_id):
                    return
                db_msg = Message(
                    external_id=incoming.external_id,
                    sender_id=incoming.sender_id,
                    sender_name=incoming.sender_name,
                    text=incoming.text,
                    status=MessageStatus.UNREAD,
                    timestamp=incoming.timestamp,
                )
                await self._msg_repo.add(session, db_msg)

        self._queue.append(db_msg)

    def queue_length(self) -> int:
        return len(self._queue)

    def cursor_position(self) -> int:
        return self._cursor
