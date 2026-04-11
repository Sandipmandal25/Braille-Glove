import asyncio
import logging
from collections.abc import Awaitable, Callable

from bleak import BleakClient, BleakScanner

from ble.gatt import BRAILLE_GLOVE_SERVICE_UUID, BUTTON_INPUT_CHAR_UUID, HAPTIC_OUTPUT_CHAR_UUID
from ble.protocol import ButtonEvent, decode_button_packet, encode_haptic_packet

log = logging.getLogger(__name__)

ButtonCallback    = Callable[[ButtonEvent], Awaitable[None]]
DisconnectCallback = Callable[[], Awaitable[None]]


class BLEManager:
    def __init__(
        self,
        on_button: ButtonCallback,
        on_disconnect: DisconnectCallback,
    ) -> None:
        self._on_button     = on_button
        self._on_disconnect = on_disconnect
        self._client: BleakClient | None = None

    async def scan_and_connect(self, timeout: float = 10.0) -> None:
        service_uuid = str(BRAILLE_GLOVE_SERVICE_UUID).lower()

        log.info("Scanning for BrailleGlove device …")
        device = await BleakScanner.find_device_by_filter(
            lambda d, adv: service_uuid in [s.lower() for s in (adv.service_uuids or [])],
            timeout=timeout,
        )
        if device is None:
            raise TimeoutError("BrailleGlove not found within scan timeout")

        log.info("Found %s (%s), connecting …", device.name, device.address)
        self._client = BleakClient(device, disconnected_callback=self._handle_disconnect)
        await self._client.connect()
        await self._client.start_notify(BUTTON_INPUT_CHAR_UUID, self._handle_notification)
        log.info("Connected to BrailleGlove")

    def _handle_disconnect(self, _client: BleakClient) -> None:
        log.warning("BrailleGlove disconnected")
        asyncio.ensure_future(self._on_disconnect())

    async def _handle_notification(self, _handle: int, data: bytes) -> None:
        try:
            event = decode_button_packet(data)
        except ValueError:
            log.warning("Malformed button packet: %s", data.hex())
            return
        await self._on_button(event)

    async def send_haptic(self, dot_mask: int, duration_ms: int) -> None:
        if self._client and self._client.is_connected:
            data = encode_haptic_packet(dot_mask, duration_ms)
            await self._client.write_gatt_char(HAPTIC_OUTPUT_CHAR_UUID, data, response=False)

    async def disconnect(self) -> None:
        if self._client:
            await self._client.disconnect()
            self._client = None

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected
