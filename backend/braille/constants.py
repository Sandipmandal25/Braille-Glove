DOT_1: int = 0b000001
DOT_2: int = 0b000010
DOT_3: int = 0b000100
DOT_4: int = 0b001000
DOT_5: int = 0b010000
DOT_6: int = 0b100000

NUMBER_INDICATOR: int = DOT_3 | DOT_4 | DOT_5 | DOT_6  # 0x3C

CELL_END_OF_MESSAGE: int = 0b01000000   # 0x40 — not a valid dot mask
CELL_SEPARATOR: int      = 0b10000000   # 0x80 — not a valid dot mask
CELL_BLANK: int          = 0x00         # all dots off (space / pause)
CELL_CONNECT_CUE: int    = 0x3F         # all six dots — "device connected" signal

DEFAULT_HAPTIC_DURATION_MS: int = 300
CUE_HAPTIC_DURATION_MS: int     = 150
INTER_CELL_GAP_MS: int          = 100
