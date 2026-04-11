import asyncio
import logging

import uvicorn

from api.app import build_fastapi_app
from core.config import get_settings
from core.queue_manager import QueueManager
from core.session import SessionManager
from db.engine import build_engine, build_session_factory, create_all_tables
from db.repository import FavoriteRepository, MessageRepository
from device.esp32 import ESP32Device
from messaging.mock_impl import MockMessaging
from messaging.telegram_impl import TelegramMessaging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
log = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()

    engine  = build_engine(settings.database_url)
    await create_all_tables(engine)
    factory = build_session_factory(engine)

    msg_repo = MessageRepository()
    fav_repo = FavoriteRepository()

    queue_mgr = QueueManager(factory, msg_repo)

    if settings.telegram_token:
        messaging = TelegramMessaging(
            token=settings.telegram_token,
            allowed_chat_ids=settings.telegram_allowed_ids,
        )
        log.info("Telegram bot enabled")
    else:
        messaging = MockMessaging()
        log.warning("No TELEGRAM_TOKEN set — running without Telegram (test mode)")

    device = ESP32Device(scan_timeout=settings.ble_scan_timeout)

    session_mgr = SessionManager(device, queue_mgr, messaging, fav_repo, factory)

    messaging.set_incoming_handler(queue_mgr.enqueue_from_external)
    device.register_button_callback(session_mgr.handle_button_event)
    device.register_connect_callback(session_mgr.on_device_connected)
    device.register_disconnect_callback(session_mgr.on_device_disconnected)

    await messaging.start()

    try:
        await device.connect()
    except Exception as exc:
        log.warning("Initial BLE connect failed (%s) — will retry when glove turns on", exc)

    app = build_fastapi_app(device, session_mgr, queue_mgr, factory, msg_repo, fav_repo)

    config = uvicorn.Config(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    log.info("API listening on %s:%d", settings.api_host, settings.api_port)

    try:
        await server.serve()
    finally:
        await messaging.stop()
        await device.disconnect()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
