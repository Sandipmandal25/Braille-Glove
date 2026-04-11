import logging
import time

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from messaging.base import AbstractMessaging, IncomingMessage, OutgoingMessage

log = logging.getLogger(__name__)


class TelegramMessaging(AbstractMessaging):
    def __init__(self, token: str, allowed_chat_ids: list[int] | None = None) -> None:
        super().__init__()
        self._token           = token
        self._allowed_ids     = set(allowed_chat_ids or [])
        self._app: Application | None = None

    async def start(self) -> None:
        self._app = Application.builder().token(self._token).build()
        self._app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_update)
        )
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(drop_pending_updates=True)
        log.info("Telegram polling started")

    async def stop(self) -> None:
        if self._app:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()

    async def send_message(self, msg: OutgoingMessage) -> None:
        if self._app is None:
            raise RuntimeError("TelegramMessaging not started")
        await self._app.bot.send_message(chat_id=int(msg.recipient_id), text=msg.text)

    async def _handle_update(self, update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None or update.message.text is None:
            return

        sender_id = update.message.from_user.id if update.message.from_user else None
        if sender_id is None:
            return

        if self._allowed_ids and sender_id not in self._allowed_ids:
            log.debug("Ignoring message from unlisted chat_id %s", sender_id)
            return

        if self._incoming_handler is None:
            return

        sender_name = (
            update.message.from_user.full_name
            if update.message.from_user
            else str(sender_id)
        )
        incoming = IncomingMessage(
            external_id=str(update.message.message_id),
            sender_id=str(sender_id),
            sender_name=sender_name,
            text=update.message.text,
            timestamp=time.time(),
        )
        await self._incoming_handler(incoming)
