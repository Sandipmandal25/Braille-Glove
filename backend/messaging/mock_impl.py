from messaging.base import AbstractMessaging, IncomingMessage, OutgoingMessage


class MockMessaging(AbstractMessaging):
    def __init__(self) -> None:
        super().__init__()
        self.sent: list[OutgoingMessage] = []

    async def send_message(self, msg: OutgoingMessage) -> None:
        self.sent.append(msg)

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def inject_message(self, msg: IncomingMessage) -> None:
        """Push a fake incoming message. Used exclusively by tests."""
        if self._incoming_handler:
            await self._incoming_handler(msg)
