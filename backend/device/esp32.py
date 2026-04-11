import asyncio
import logging

from ble.manager import BLEManager
from ble.protocol import ButtonEvent
from device.base import AbstractDevice, ButtonCallback, LifecycleCallback

log = logging.getLogger(__name__)

_MAX_RECONNECT_DELAY = 60.0
_INTER_CELL_GAP_S    = 0.1


class ESP32Device(AbstractDevice):
    def __init__(self, scan_timeout: float = 10.0) -> None:
        self._scan_timeout         = scan_timeout
        self._manager:             BLEManager       | None = None
        self._button_callback:     ButtonCallback    | None = None
        self._connect_callback:    LifecycleCallback | None = None
        self._disconnect_callback: LifecycleCallback | None = None
        self._reconnect_task:      asyncio.Task      | None = None

    def register_button_callback(self, cb: ButtonCallback) -> None:
        self._button_callback = cb

    def register_connect_callback(self, cb: LifecycleCallback) -> None:
        self._connect_callback = cb

    def register_disconnect_callback(self, cb: LifecycleCallback) -> None:
        self._disconnect_callback = cb

    async def connect(self) -> None:
        self._manager = BLEManager(
            on_button=self._dispatch_button,
            on_disconnect=self._on_ble_disconnect,
        )
        await self._manager.scan_and_connect(timeout=self._scan_timeout)
        if self._connect_callback:
            await self._connect_callback()

    async def disconnect(self) -> None:
        if self._reconnect_task:
            self._reconnect_task.cancel()
            self._reconnect_task = None
        if self._manager:
            await self._manager.disconnect()
            self._manager = None

    async def send_haptic_cell(self, dot_mask: int, duration_ms: int) -> None:
        if self._manager:
            await self._manager.send_haptic(dot_mask, duration_ms)

    async def send_haptic_sequence(self, cells: list[tuple[int, int]]) -> None:
        for dot_mask, duration_ms in cells:
            await self.send_haptic_cell(dot_mask, duration_ms)
            await asyncio.sleep(_INTER_CELL_GAP_S)

    @property
    def is_connected(self) -> bool:
        return self._manager is not None and self._manager.is_connected

    async def _dispatch_button(self, event: ButtonEvent) -> None:
        if self._button_callback:
            await self._button_callback(event)

    async def _on_ble_disconnect(self) -> None:
        if self._disconnect_callback:
            await self._disconnect_callback()
        self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        delay = 5.0
        while not self.is_connected:
            log.info("Reconnecting in %.0fs …", delay)
            await asyncio.sleep(delay)
            try:
                await self.connect()
                return
            except Exception as exc:
                log.warning("Reconnect failed: %s", exc)
                delay = min(delay * 2, _MAX_RECONNECT_DELAY)
