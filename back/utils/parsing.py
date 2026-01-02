import re
from typing import List, Optional, TypedDict


class Choice(TypedDict):
    text: str
    roll: Optional[str]

def parse_choices(text: str) -> List[Choice]:
    """
    Parses choices from the text.
    Expected format:
    --CHOICES
    1. Choice text [Roll: skill_id]
    2. Another choice
    """
    choices: List[Choice] = []
    
    # Find the choices block
    match = re.search(r"--CHOICES\s*(.*)", text, re.DOTALL)
    if not match:
        return choices
        
    block = match.group(1)
    
    # Iterate over lines
    for line in block.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # Match pattern: "1. Text [Roll: skill]" or "1. Text"
        # We handle various numbering formats: "1.", "1)", "-", "*"
        # But the prompt will request numbered list.
        
        # Regex to capture:
        # ^(?:\d+[.)]|-|\*)\s+  -> Numbering/Bullet
        # (.*?)                 -> Text (lazy)
        # (?:\s*\[Roll:\s*(.*?)\])? -> Optional Roll
        # $
        
        choice_match = re.match(r"^(?:\d+[.)]|-|\*)\s+(.*?)(?:\s*\[Roll:\s*(.*?)\])?$", line)
        if choice_match:
            text_part = choice_match.group(1).strip()
            roll_part = choice_match.group(2)
            
            choices.append({
                "text": text_part,
                "roll": roll_part.strip() if roll_part else None
            })
            
    return choices
