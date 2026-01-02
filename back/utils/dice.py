import random
import re

# Jets de dés

def roll_dice(dice_str: str) -> int:
    """
    Parses and rolls a dice string (e.g., '1d8', '2d6+1').

    Args:
        dice_str (str): The dice string to roll.

    Returns:
        int: The total result of the roll.
    """
    try:
        # Remove whitespace
        dice_str = dice_str.replace(" ", "")
        
        # Check for static number
        if dice_str.isdigit():
            return int(dice_str)
            
        # Parse XdY+Z
        match = re.match(r"(\d+)d(\d+)(?:([+-])(\d+))?", dice_str)
        if match:
            count = int(match.group(1))
            sides = int(match.group(2))
            modifier_sign = match.group(3)
            modifier = int(match.group(4)) if match.group(4) else 0
            
            total = sum(random.randint(1, sides) for _ in range(count))
            
            if modifier_sign == '-':
                total -= modifier
            elif modifier_sign == '+':
                total += modifier
                
            return max(1, total)
        return 1 # Fallback
    except Exception:
        return 1

def roll_attack(dice: str) -> int:
    """
    Effectue un jet d'attaque en lançant les dés spécifiés.
    Alias pour roll_dice pour compatibilité.

    Parameters:
    - dice (str): La notation des dés à lancer (ex: "1d20").

    Returns:
    - int: Le résultat du jet d'attaque.
    """
    return roll_dice(dice)
