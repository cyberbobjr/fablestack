import pytest

from back.utils.parsing import parse_choices


def test_parse_choices_simple():
    text = """
    Some narrative text.
    
    --CHOICES
    1. Attack the goblin [Roll: strength]
    2. Run away
    """
    choices = parse_choices(text)
    assert len(choices) == 2
    assert choices[0]["text"] == "Attack the goblin"
    assert choices[0]["roll"] == "strength"
    assert choices[1]["text"] == "Run away"
    assert choices[1]["roll"] is None

def test_parse_choices_no_choices():
    text = "Just some text."
    choices = parse_choices(text)
    assert len(choices) == 0

def test_parse_choices_messy_format():
    text = """
    --CHOICES
    1. Option 1
    2. Option 2 [Roll: agility]
    3. Option 3 [Roll: wisdom] 
    """
    choices = parse_choices(text)
    assert len(choices) == 3
    assert choices[2]["text"] == "Option 3"
    assert choices[2]["roll"] == "wisdom"

def test_parse_choices_with_bullets():
    text = """
    --CHOICES
    - Option A
    * Option B [Roll: int]
    """
    choices = parse_choices(text)
    assert len(choices) == 2
    assert choices[0]["text"] == "Option A"
    assert choices[1]["text"] == "Option B"
    assert choices[1]["roll"] == "int"
