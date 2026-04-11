from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Favorite, Message, MessageStatus


class MessageRepository:
    async def add(self, session: AsyncSession, msg: Message) -> Message:
        session.add(msg)
        await session.flush()
        return msg

    async def get_by_external_id(
        self, session: AsyncSession, external_id: str
    ) -> Message | None:
        result = await session.execute(
            select(Message).where(Message.external_id == external_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, session: AsyncSession, message_id: int) -> Message | None:
        result = await session.execute(
            select(Message).where(Message.id == message_id)
        )
        return result.scalar_one_or_none()

    async def list_unread(self, session: AsyncSession) -> list[Message]:
        result = await session.execute(
            select(Message)
            .where(Message.status == MessageStatus.UNREAD)
            .order_by(Message.timestamp.asc())
        )
        return list(result.scalars().all())

    async def list_read(self, session: AsyncSession) -> list[Message]:
        result = await session.execute(
            select(Message)
            .where(Message.status == MessageStatus.READ)
            .order_by(Message.timestamp.desc())
        )
        return list(result.scalars().all())

    async def list_all(
        self, session: AsyncSession, limit: int = 100, offset: int = 0
    ) -> list[Message]:
        result = await session.execute(
            select(Message).order_by(Message.timestamp.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def count_all(self, session: AsyncSession) -> int:
        result = await session.execute(select(func.count()).select_from(Message))
        return result.scalar_one()

    async def mark_read(self, session: AsyncSession, message_id: int) -> None:
        await session.execute(
            update(Message)
            .where(Message.id == message_id)
            .values(status=MessageStatus.READ)
        )

    async def delete_by_id(self, session: AsyncSession, message_id: int) -> bool:
        msg = await self.get_by_id(session, message_id)
        if msg is None:
            return False
        await session.delete(msg)
        await session.flush()
        return True

    async def count_unread(self, session: AsyncSession) -> int:
        result = await session.execute(
            select(func.count()).where(Message.status == MessageStatus.UNREAD)
        )
        return result.scalar_one()


class FavoriteRepository:
    async def upsert(self, session: AsyncSession, fav: Favorite) -> Favorite:
        existing = await self.get_by_slot(session, fav.slot)
        if existing:
            existing.name        = fav.name
            existing.telegram_id = fav.telegram_id
            await session.flush()
            return existing
        session.add(fav)
        await session.flush()
        return fav

    async def get_by_slot(self, session: AsyncSession, slot: int) -> Favorite | None:
        result = await session.execute(
            select(Favorite).where(Favorite.slot == slot)
        )
        return result.scalar_one_or_none()

    async def list_all(self, session: AsyncSession) -> list[Favorite]:
        result = await session.execute(
            select(Favorite).order_by(Favorite.slot.asc())
        )
        return list(result.scalars().all())

    async def delete_by_slot(self, session: AsyncSession, slot: int) -> None:
        fav = await self.get_by_slot(session, slot)
        if fav:
            await session.delete(fav)
            await session.flush()

    async def count(self, session: AsyncSession) -> int:
        result = await session.execute(select(func.count()).select_from(Favorite))
        return result.scalar_one()
