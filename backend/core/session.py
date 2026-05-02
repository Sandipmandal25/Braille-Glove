import logging
from dataclasses import dataclass, field
from enum import Enum, auto

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ble.protocol import ButtonEvent, ButtonType, EventType
from braille.charset import GRADE1_MAP
from braille.codec import decode_single_chord, encode_text
from braille.constants import (
    CELL_BLANK,
    CELL_CONNECT_CUE,
    CELL_END_OF_MESSAGE,
    CELL_SEPARATOR,
    CUE_HAPTIC_DURATION_MS,
    DEFAULT_HAPTIC_DURATION_MS,
)
from core.queue_manager import QueueManager
from db.models import Message
from db.repository import FavoriteRepository
from device.base import AbstractDevice
from messaging.base import AbstractMessaging, OutgoingMessage

log = logging.getLogger(__name__)


class GloveMode(Enum):
    READ    = auto()
    COMPOSE = auto()


@dataclass
class ComposeState:
    typed_text:    str  = field(default_factory=str)
    favorite_slot: int  = 0
    number_mode:   bool = False


class SessionManager:
    """
    Central state machine that ties the device, queue, and messaging together.

    Receives button events from the glove and drives haptic output in return.
    Two modes:
      READ    — navigate incoming messages with PREV/NEXT
      COMPOSE — type a Braille reply and send to a selected favorite
    """

    def __init__(
        self,
        device:          AbstractDevice,
        queue_manager:   QueueManager,
        messaging:       AbstractMessaging,
        fav_repo:        FavoriteRepository,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._device   = device
        self._queue    = queue_manager
        self._msg      = messaging
        self._fav_repo = fav_repo
        self._factory  = session_factory
        self._mode     = GloveMode.READ
        self._compose  = ComposeState()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def on_device_connected(self) -> None:
        await self._queue.load_unread()
        self._mode    = GloveMode.READ
        self._compose = ComposeState()
        await self._device.send_haptic_cell(CELL_CONNECT_CUE, CUE_HAPTIC_DURATION_MS)
        msg = await self._queue.current_message()
        if msg:
            await self._play_message(msg)

    async def on_new_message(self) -> None:
        """Auto-play a newly arrived message if in READ mode and glove is connected."""
        if self._mode != GloveMode.READ:
            log.info("New message ignored — not in READ mode")
            return
        if not self._device.is_connected:
            log.info("New message ignored — glove not connected")
            return
        msg = await self._queue.jump_to_latest()
        if msg:
            log.info("Auto-playing new message: %r", msg.text)
            await self._play_message(msg)

    async def on_device_disconnected(self) -> None:
        self._mode    = GloveMode.READ
        self._compose = ComposeState()
        log.info("Glove disconnected — session state reset")

    # ------------------------------------------------------------------
    # Button dispatch
    # ------------------------------------------------------------------

    async def handle_button_event(self, event: ButtonEvent) -> None:
        if self._mode == GloveMode.READ:
            await self._handle_read(event)
        else:
            await self._handle_compose(event)

    async def _handle_read(self, event: ButtonEvent) -> None:
        match (event.button, event.event):
            case (ButtonType.PREV, EventType.SINGLE_TAP):
                msg = await self._queue.retreat()
                if msg:
                    await self._play_message(msg)

            case (ButtonType.NEXT, EventType.SINGLE_TAP):
                msg = await self._queue.advance()
                if msg:
                    await self._play_message(msg)

            case (ButtonType.ENTER, EventType.SINGLE_TAP):
                await self._queue.mark_current_read()

            case (ButtonType.PREV, EventType.DOUBLE_TAP):
                msg = await self._queue.jump_to_oldest_unread()
                if msg:
                    await self._play_message(msg)

            case (ButtonType.NEXT, EventType.DOUBLE_TAP):
                await self._switch_mode(GloveMode.COMPOSE)

    async def _handle_compose(self, event: ButtonEvent) -> None:
        match (event.button, event.event):
            case (ButtonType.BRAILLE, EventType.SINGLE_TAP):
                await self._handle_braille_chord(event.dot_mask or 0)

            case (ButtonType.PREV, EventType.SINGLE_TAP):
                await self._scroll_favorite(direction=-1)

            case (ButtonType.NEXT, EventType.SINGLE_TAP):
                await self._scroll_favorite(direction=1)

            case (ButtonType.ENTER, EventType.SINGLE_TAP):
                if self._compose.typed_text:
                    await self._send_composed_message()

            case (ButtonType.PREV, EventType.DOUBLE_TAP):
                await self._backspace()

            case (ButtonType.NEXT, EventType.DOUBLE_TAP):
                await self._switch_mode(GloveMode.READ)

    # ------------------------------------------------------------------
    # Compose helpers
    # ------------------------------------------------------------------

    async def _handle_braille_chord(self, dot_mask: int) -> None:
        char, new_num_mode = decode_single_chord(dot_mask, self._compose.number_mode)
        self._compose.number_mode = new_num_mode
        if char and char != "?":
            self._compose.typed_text += char
            cell = GRADE1_MAP.get(char, CELL_BLANK)
            await self._device.send_haptic_cell(cell, CUE_HAPTIC_DURATION_MS)

    async def _scroll_favorite(self, direction: int) -> None:
        async with self._factory() as session:
            count = await self._fav_repo.count(session)
        if count == 0:
            return
        self._compose.favorite_slot = (self._compose.favorite_slot + direction) % count
        await self._play_contact_name(self._compose.favorite_slot)

    async def _backspace(self) -> None:
        if self._compose.typed_text:
            self._compose.typed_text = self._compose.typed_text[:-1]
        await self._device.send_haptic_cell(CELL_BLANK, CUE_HAPTIC_DURATION_MS)

    async def _send_composed_message(self) -> None:
        async with self._factory() as session:
            fav = await self._fav_repo.get_by_slot(session, self._compose.favorite_slot)
        if fav is None:
            log.warning("No favorite at slot %d", self._compose.favorite_slot)
            return
        out = OutgoingMessage(recipient_id=fav.telegram_id, text=self._compose.typed_text)
        await self._msg.send_message(out)
        log.info("Sent to %s: %r", fav.name, self._compose.typed_text)
        self._compose.typed_text  = ""
        self._compose.number_mode = False
        await self._device.send_haptic_cell(CELL_END_OF_MESSAGE, DEFAULT_HAPTIC_DURATION_MS)

    # ------------------------------------------------------------------
    # Haptic output
    # ------------------------------------------------------------------

    async def _play_message(self, msg: Message) -> None:
        cells = encode_text(msg.text)
        sequence = [(cell, DEFAULT_HAPTIC_DURATION_MS) for cell in cells]
        sequence.append((CELL_END_OF_MESSAGE, CUE_HAPTIC_DURATION_MS))
        await self._device.send_haptic_sequence(sequence)

    async def _play_contact_name(self, slot: int) -> None:
        async with self._factory() as session:
            fav = await self._fav_repo.get_by_slot(session, slot)
        if fav is None:
            return
        cells = encode_text(fav.name)
        sequence = [(cell, DEFAULT_HAPTIC_DURATION_MS) for cell in cells]
        await self._device.send_haptic_sequence(sequence)

    async def _switch_mode(self, new_mode: GloveMode) -> None:
        if new_mode == GloveMode.COMPOSE:
            await self._device.send_haptic_cell(CELL_SEPARATOR, CUE_HAPTIC_DURATION_MS)
            await self._device.send_haptic_cell(CELL_SEPARATOR, CUE_HAPTIC_DURATION_MS)
            self._compose = ComposeState()
            await self._play_contact_name(self._compose.favorite_slot)
        else:
            await self._device.send_haptic_cell(CELL_END_OF_MESSAGE, CUE_HAPTIC_DURATION_MS)
            self._compose = ComposeState()
        self._mode = new_mode
        log.info("Mode → %s", new_mode.name)

    # ------------------------------------------------------------------
    # Properties (read by API layer)
    # ------------------------------------------------------------------

    @property
    def mode(self) -> GloveMode:
        return self._mode

    @property
    def compose_slot(self) -> int:
        return self._compose.favorite_slot

    @property
    def compose_text(self) -> str:
        return self._compose.typed_text
