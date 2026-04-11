from braille.charset import DIGIT_CELLS, DIGIT_CELLS_REVERSE, GRADE1_MAP, REVERSE_MAP
from braille.constants import CELL_BLANK, NUMBER_INDICATOR


def encode_text(text: str) -> list[int]:
    """
    Convert a plain-text string to an ordered list of 6-bit dot masks.

    Lowercases input. Inserts NUMBER_INDICATOR before each run of digits.
    Unknown characters are silently skipped.
    """
    result: list[int] = []
    in_number_mode = False

    for char in text.lower():
        if char in DIGIT_CELLS:
            if not in_number_mode:
                result.append(NUMBER_INDICATOR)
                in_number_mode = True
            result.append(DIGIT_CELLS[char])
        else:
            in_number_mode = False
            if char in GRADE1_MAP:
                result.append(GRADE1_MAP[char])

    return result


def decode_chord_sequence(chords: list[int]) -> str:
    """
    Convert a list of 6-bit chord values to a plain-text string.
    Handles NUMBER_INDICATOR state internally.
    """
    text = ""
    number_mode = False
    for chord in chords:
        char, number_mode = decode_single_chord(chord, number_mode)
        text += char
    return text


def decode_single_chord(chord: int, number_mode: bool) -> tuple[str, bool]:
    """
    Decode one chord value.

    Returns (character, new_number_mode).
    Returns ('', True) for the NUMBER_INDICATOR cell.
    Returns ('?', number_mode) for unknown chords.
    """
    if chord == NUMBER_INDICATOR:
        return ("", True)

    if chord == CELL_BLANK:
        return (" ", False)

    if number_mode:
        char = DIGIT_CELLS_REVERSE.get(chord, "?")
        return (char, char.isdigit())

    char = REVERSE_MAP.get(chord, "?")
    return (char, False)
