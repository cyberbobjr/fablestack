"""Password validation utilities for authentication."""

import re
from typing import List


def validate_password_strength(password: str) -> tuple[bool, List[str]]:
    """
    Validate password strength according to security requirements.
    
    Requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    - Contains at least one special character
    
    Args:
        password: The password to validate
        
    Returns:
        A tuple of (is_valid, list_of_errors)
        If is_valid is True, list_of_errors will be empty
        Otherwise, list_of_errors contains human-readable error messages
    """
    errors: List[str] = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one digit")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>\+]', password):
        errors.append("Password must contain at least one special character")
    
    is_valid: bool = len(errors) == 0
    return is_valid, errors
