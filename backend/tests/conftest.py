import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.queue_manager import QueueManager
from core.session import SessionManager
from db.engine import build_engine, build_session_factory, create_all_tables
from db.repository import FavoriteRepository, MessageRepository
from device.simulator import SimulatorDevice
from messaging.mock_impl import MockMessaging


@pytest.fixture
def sim_device() -> SimulatorDevice:
    return SimulatorDevice()


@pytest.fixture
def mock_messaging() -> MockMessaging:
    return MockMessaging()


@pytest.fixture
async def db_session_factory(tmp_path) -> async_sessionmaker[AsyncSession]:
    engine = build_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    await create_all_tables(engine)
    factory = build_session_factory(engine)
    yield factory
    await engine.dispose()


@pytest.fixture
def msg_repo() -> MessageRepository:
    return MessageRepository()


@pytest.fixture
def fav_repo() -> FavoriteRepository:
    return FavoriteRepository()


@pytest.fixture
async def queue_manager(
    db_session_factory, msg_repo
) -> QueueManager:
    return QueueManager(db_session_factory, msg_repo)


@pytest.fixture
async def session_manager(
    sim_device, mock_messaging, queue_manager, fav_repo, db_session_factory
) -> SessionManager:
    sm = SessionManager(sim_device, queue_manager, mock_messaging, fav_repo, db_session_factory)
    sim_device.register_button_callback(sm.handle_button_event)
    sim_device.register_connect_callback(sm.on_device_connected)
    sim_device.register_disconnect_callback(sm.on_device_disconnected)
    await sim_device.connect()
    return sm
