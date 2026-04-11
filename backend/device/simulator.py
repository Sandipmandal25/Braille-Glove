"""
In-process software device for testing — no BLE hardware required.

Usage in tests:
    device = SimulatorDevice()
    device.register_button_callback(handler)
    device.register_connect_callback(on_connect)
    await device.connect()                        # triggers on_connect

    await device.inject_button_event(event)       # drives input
    assert device.haptic_log == [(0x01, 300), …]  # asserts output
"""

import asyncio

from ble.protocol import ButtonEvent
from device.base import AbstractDevice, ButtonCallback, LifecycleCallback


class SimulatorDevice(AbstractDevice):
    def __init__(self) -> None:
        self.haptic_log: list[tuple[int, int]] = []
        self._connected             = False
        self._button_callback:     ButtonCallback    | None = None
        self._connect_callback:    LifecycleCallback | None = None
        self._disconnect_callback: LifecycleCallback | None = None

    def register_button_callback(self, cb: ButtonCallback) -> None:
        self._button_callback = cb

    def register_connect_callback(self, cb: LifecycleCallback) -> None:
        self._connect_callback = cb

    def register_disconnect_callback(self, cb: LifecycleCallback) -> None:
        self._disconnect_callback = cb

    async def connect(self) -> None:
        self._connected = True
        if self._connect_callback:
            await self._connect_callback()

    async def disconnect(self) -> None:
        self._connected = False
        if self._disconnect_callback:
            await self._disconnect_callback()

    async def send_haptic_cell(self, dot_mask: int, duration_ms: int) -> None:
        self.haptic_log.append((dot_mask, duration_ms))

    async def send_haptic_sequence(self, cells: list[tuple[int, int]]) -> None:
        for dot_mask, duration_ms in cells:
            self.haptic_log.append((dot_mask, duration_ms))

    async def inject_button_event(self, event: ButtonEvent) -> None:
        """Push a button event directly to the registered callback."""
        if self._button_callback:
            await self._button_callback(event)

    def clear_haptic_log(self) -> None:
        self.haptic_log.clear()

    @property
    def is_connected(self) -> bool:
        return self._connected
