"""
Custom exceptions for the FableStack project.
"""

class FableStackError(Exception):
    """Base class for all FableStack exceptions."""
    pass

class ServiceNotInitializedError(FableStackError):
    """Raised when a service is accessed but not initialized."""
    pass

class SessionNotFoundError(FableStackError):
    """Raised when a session cannot be found."""
    pass

class CharacterNotFoundError(FableStackError):
    """Raised when a character cannot be found."""
    pass

class CharacterInvalidStateError(FableStackError):
    """Raised when a character is in an invalid state (e.g. draft)."""
    pass

class InternalServerError(FableStackError):
    """Raised when an unexpected error occurs."""
    pass

class ScenarioNotFoundError(FableStackError):
    """Raised when a scenario cannot be found."""
    pass
