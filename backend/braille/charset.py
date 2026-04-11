"""
Grade-1 English Braille character map.

Bit layout (LSB = dot 1):
  bit 0 = dot 1  (top-left)
  bit 1 = dot 2  (mid-left)
  bit 2 = dot 3  (bot-left)
  bit 3 = dot 4  (top-right)
  bit 4 = dot 5  (mid-right)
  bit 5 = dot 6  (bot-right)
"""

GRADE1_MAP: dict[str, int] = {
    # Letters
    "a": 0x01,  # 1
    "b": 0x03,  # 12
    "c": 0x09,  # 14
    "d": 0x19,  # 145
    "e": 0x11,  # 15
    "f": 0x0B,  # 124
    "g": 0x1B,  # 1245
    "h": 0x13,  # 125
    "i": 0x0A,  # 24
    "j": 0x1A,  # 245
    "k": 0x05,  # 13
    "l": 0x07,  # 123
    "m": 0x0D,  # 134
    "n": 0x1D,  # 1345
    "o": 0x15,  # 135
    "p": 0x0F,  # 1234
    "q": 0x1F,  # 12345
    "r": 0x17,  # 1235
    "s": 0x0E,  # 234
    "t": 0x1E,  # 2345
    "u": 0x25,  # 136
    "v": 0x27,  # 1236
    "w": 0x3A,  # 2456
    "x": 0x2D,  # 1346
    "y": 0x3D,  # 13456
    "z": 0x35,  # 1356
    # Punctuation
    " ":  0x00,  # blank cell
    ",":  0x02,  # 2
    ";":  0x06,  # 23
    ":":  0x12,  # 25
    ".":  0x32,  # 256
    "!":  0x16,  # 235
    "?":  0x26,  # 236
    "'":  0x04,  # 3
    "-":  0x24,  # 36
    "\n": 0x00,  # treat newline as space
}

# Digits use the same cell patterns as a–j (encoder inserts NUMBER_INDICATOR prefix)
DIGIT_CELLS: dict[str, int] = {
    "1": 0x01,
    "2": 0x03,
    "3": 0x09,
    "4": 0x19,
    "5": 0x11,
    "6": 0x0B,
    "7": 0x1B,
    "8": 0x13,
    "9": 0x0A,
    "0": 0x1A,
}

REVERSE_MAP: dict[int, str]       = {v: k for k, v in GRADE1_MAP.items() if k != "\n"}
DIGIT_CELLS_REVERSE: dict[int, str] = {v: k for k, v in DIGIT_CELLS.items()}
