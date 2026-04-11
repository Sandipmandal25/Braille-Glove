# BLE Communication Protocol

## GATT Layout

| Role | UUID |
|------|------|
| Service | `a1b2c3d4-0001-4e5f-8000-000000000001` |
| HAPTIC_OUTPUT (write-without-response) | `a1b2c3d4-0001-4e5f-8000-000000000002` |
| BUTTON_INPUT (notify) | `a1b2c3d4-0001-4e5f-8000-000000000003` |

The ESP32 advertises the service UUID so the Python backend can find it by scanning.

---

## Haptic Packet — Backend → ESP32 (2 bytes)

```
byte[0]  dot_mask    bits 0-5 = Braille dots 1-6
                     bits 6-7 set = special code (not a Braille cell)
byte[1]  duration    actual_ms = value × 10   (range: 10 – 2550 ms)
```

### Special dot_mask values

| Value | Constant | Meaning |
|-------|----------|---------|
| `0x00` | `CELL_BLANK` | All dots off — space or inter-cell gap |
| `0x3C` | `NUMBER_INDICATOR` | Braille number indicator (dots 3,4,5,6) |
| `0x3F` | `CELL_CONNECT_CUE` | All six dots — "glove connected" signal |
| `0x40` | `CELL_END_OF_MESSAGE` | End of message / send confirmation |
| `0x80` | `CELL_SEPARATOR` | Mode-change cue (sent twice = entering COMPOSE) |

---

## Button Packet — ESP32 → Backend

### Non-Braille buttons (1 byte)

```
bits 7-4  ButtonType    PREV=0x1  NEXT=0x2  ENTER=0x3
bits 3-0  EventType     SINGLE_TAP=0x0  DOUBLE_TAP=0x1
```

### Braille chord (2 bytes)

```
byte[0] = 0x00        (BRAILLE type, SINGLE_TAP)
byte[1] = dot_mask    bits 0-5 = dots 1-6
```

---

## Braille Dot Bit Layout

```
Dot positions:   Bit positions:
  1  4             0  3
  2  5             1  4
  3  6             2  5
```

Example: letter **a** = dot 1 = `0b000001` = `0x01`

---

## Session State Machine

```
[device connects]
       │
       ▼
    READ mode  ◄──────────────────────────────────────────┐
       │                                                   │
  PREV single → retreat queue → play message              │
  NEXT single → advance queue → play message              │
  ENTER single → mark current read                        │
  PREV double → jump to oldest unread                     │
  NEXT double ──────────────────────────────────────► COMPOSE mode
                                                          │
                                              6-dot chord → decode → typed_text
                                              PREV single → scroll favorites backward
                                              NEXT single → scroll favorites forward
                                              ENTER single → send to selected favorite
                                              PREV double → backspace
                                              NEXT double ──────────────────────────►
```
