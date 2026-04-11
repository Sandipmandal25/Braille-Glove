import enum

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MessageStatus(str, enum.Enum):
    UNREAD = "unread"
    READ   = "read"


class Message(Base):
    __tablename__ = "messages"

    id:          Mapped[int]   = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str]   = mapped_column(String, unique=True, index=True)
    sender_id:   Mapped[str]   = mapped_column(String, index=True)
    sender_name: Mapped[str]   = mapped_column(String)
    text:        Mapped[str]   = mapped_column(String)
    status:      Mapped[str]   = mapped_column(String, default=MessageStatus.UNREAD)
    timestamp:   Mapped[float] = mapped_column(Float, index=True)


class Favorite(Base):
    __tablename__ = "favorites"

    id:          Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slot:        Mapped[int] = mapped_column(Integer, unique=True)   # 0–9
    name:        Mapped[str] = mapped_column(String)
    telegram_id: Mapped[str] = mapped_column(String, unique=True)
