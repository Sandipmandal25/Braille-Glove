import pytest

from braille.charset import GRADE1_MAP
from braille.codec import decode_chord_sequence, decode_single_chord, encode_text
from braille.constants import CELL_BLANK, NUMBER_INDICATOR


def test_encode_single_letter():
    assert encode_text("a") == [GRADE1_MAP["a"]]


def test_encode_lowercases_input():
    assert encode_text("A") == encode_text("a")


def test_encode_space():
    assert encode_text(" ") == [CELL_BLANK]


def test_encode_digit_inserts_number_indicator():
    result = encode_text("1")
    assert result[0] == NUMBER_INDICATOR
    assert len(result) == 2


def test_encode_digit_run_single_indicator():
    result = encode_text("123")
    assert result.count(NUMBER_INDICATOR) == 1
    assert len(result) == 4  # indicator + three digits


def test_encode_number_indicator_resets_on_letter():
    result = encode_text("1a")
    assert result[0] == NUMBER_INDICATOR  # indicator for digit
    assert result[2] == GRADE1_MAP["a"]   # letter after digit


def test_encode_unknown_char_skipped():
    assert encode_text("\x00") == []
    assert encode_text("€") == []


def test_encode_word():
    result = encode_text("hi")
    assert result == [GRADE1_MAP["h"], GRADE1_MAP["i"]]


def test_decode_single_chord_letter():
    char, num_mode = decode_single_chord(GRADE1_MAP["a"], False)
    assert char == "a"
    assert num_mode is False


def test_decode_number_indicator_sets_mode():
    char, num_mode = decode_single_chord(NUMBER_INDICATOR, False)
    assert char == ""
    assert num_mode is True


def test_decode_digit_in_number_mode():
    from braille.charset import DIGIT_CELLS
    char, num_mode = decode_single_chord(DIGIT_CELLS["3"], True)
    assert char == "3"
    assert num_mode is True


def test_decode_space_resets_number_mode():
    char, num_mode = decode_single_chord(CELL_BLANK, True)
    assert char == " "
    assert num_mode is False


def test_decode_unknown_chord_returns_question():
    char, _ = decode_single_chord(0x3E, False)
    assert char == "?"


def test_roundtrip_simple_word():
    original = "hello"
    chords = encode_text(original)
    decoded = decode_chord_sequence(chords)
    assert decoded == original


def test_roundtrip_with_digits():
    original = "room 42"
    chords = encode_text(original)
    decoded = decode_chord_sequence(chords)
    assert decoded == original


def test_roundtrip_punctuation():
    for ch in ",.!?":
        chords = encode_text(ch)
        decoded = decode_chord_sequence(chords)
        assert decoded == ch, f"Failed round-trip for {ch!r}"
