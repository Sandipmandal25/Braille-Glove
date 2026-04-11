"""
BLE wire format between the Python backend and the ESP32 glove.

Haptic packet  (backend → ESP32, 2 bytes):
  byte[0] = dot_mask  — bits 0-5 are Braille dots 1-6;
                         bits 6-7 are set for special codes (CELL_*)
  byte[1] = duration  — actual_ms = value × 10  (clamped to 10–2550 ms)

Button packet  (ESP32 → backend):
  Non-Braille (1 byte):
    high nibble = ButtonType  (PREV=0x1, NEXT=0x2, ENTER=0x3)
    low  nibble = EventType   (SINGLE_TAP=0x0, DOUBLE_TAP=0x1)
  Braille (2 bytes):
    byte[0] = 0x00  (BRAILLE type, SINGLE_TAP)
    byte[1] = 6-bit dot mask
"""

from dataclasses import dataclass
from enum import IntEnum


class ButtonType(IntEnum):
    BRAILLE = 0x0
    PREV    = 0x1
    NEXT    = 0x2
    ENTER   = 0x3


class EventType(IntEnum):
    SINGLE_TAP = 0x0
    DOUBLE_TAP = 0x1


@dataclass(frozen=True)
class ButtonEvent:
    button:   ButtonType
    event:    EventType
    dot_mask: int | None = None  # only set when button == BRAILLE


def encode_haptic_packet(dot_mask: int, duration_ms: int) -> bytes:
    """Pack a haptic command into 2 bytes."""
    clamped = max(10, min(2550, duration_ms))
    return bytes([dot_mask & 0xFF, clamped // 10])


def decode_button_packet(data: bytes) -> ButtonEvent:
    """
    Parse a 1-byte or 2-byte BLE notification into a ButtonEvent.
    Raises ValueError on malformed input.
    """
    if not data:
        raise ValueError("Empty button packet")

    if len(data) == 2 and data[0] == 0x00:
        return ButtonEvent(
            button=ButtonType.BRAILLE,
            event=EventType.SINGLE_TAP,
            dot_mask=data[1] & 0x3F,
        )

    if len(data) == 1:
        btn_nibble   = (data[0] >> 4) & 0x0F
        event_nibble = data[0] & 0x0F
        try:
            button = ButtonType(btn_nibble)
            event  = EventType(event_nibble)
        except ValueError as exc:
            raise ValueError(f"Unknown button nibble in packet: {data.hex()}") from exc
        return ButtonEvent(button=button, event=event)

    raise ValueError(f"Unexpected button packet length {len(data)}: {data.hex()}")
