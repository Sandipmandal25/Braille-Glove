from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass
class IncomingMessage:
    external_id:  str
    sender_id:    str
    sender_name:  str
    text:         str
    timestamp:    float  # unix epoch


@dataclass
class OutgoingMessage:
    recipient_id: str
    text:         str


IncomingHandler = Callable[[IncomingMessage], Awaitable[None]]


class AbstractMessaging(ABC):
    def __init__(self) -> None:
        self._incoming_handler: IncomingHandler | None = None

    def set_incoming_handler(self, handler: IncomingHandler) -> None:
        self._incoming_handler = handler

    @abstractmethod
    async def send_message(self, msg: OutgoingMessage) -> None: ...

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...
