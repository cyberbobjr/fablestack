"""
Tests for the logging utility functions.
Validates that logging functions work correctly and don't conflict with LogRecord attributes.
"""

import pytest
from back.utils.logger import log_debug, log_info, log_warning, log_error, log_critical


def test_log_debug_basic():
    """Test that log_debug works with basic message"""
    # Should not raise any exception
    log_debug("Test debug message", action="test", value=42)


def test_log_info_basic():
    """Test that log_info works with basic message"""
    log_info("Test info message", action="test", value=42)


def test_log_warning_basic():
    """Test that log_warning works with basic message"""
    log_warning("Test warning message", action="test", value=42)


def test_log_error_basic():
    """Test that log_error works with basic message"""
    log_error("Test error message", action="test", value=42)


def test_log_critical_basic():
    """Test that log_critical works with basic message"""
    log_critical("Test critical message", action="test", value=42)


def test_log_debug_with_reserved_attribute():
    """Test that log_debug raises error when reserved attribute is passed"""
    # 'message' as kwarg causes TypeError from Python itself (duplicate argument)
    # This is intentional - we're testing that Python catches this error
    with pytest.raises(TypeError, match="got multiple values for argument 'message'"):
        log_debug("Test message", **{"message": "This should fail"})  # Using ** to bypass IDE warnings


def test_log_debug_with_other_reserved_attributes():
    """Test that log_debug safely handles reserved attributes by renaming them"""
    # Should not raise ValueError anymore, as functionality was updated to safe-rename
    try:
        log_debug("Test message", levelname="CUSTOM", pathname="/some/path")
    except ValueError:
        pytest.fail("log_debug raised ValueError unexpectedly")


def test_log_debug_with_complex_data():
    """Test that log_debug works with complex data structures"""
    log_debug(
        "Complex test",
        action="complex_test",
        character_id="123-456",
        stats={"strength": 15, "agility": 12},
        items=["sword", "shield"],
        count=5
    )


def test_log_functions_with_various_kwargs():
    """Test that all log functions work with various kwargs"""
    common_kwargs = {
        "action": "test_action",
        "character_id": "test-123",
        "count": 10,
        "success": True
    }
    
    log_debug("Debug test", **common_kwargs)
    log_info("Info test", **common_kwargs)
    log_warning("Warning test", **common_kwargs)
    log_error("Error test", **common_kwargs)
    log_critical("Critical test", **common_kwargs)


def test_log_with_none_values():
    """Test that logging works with None values"""
    log_debug("Test with None", value=None, optional_field=None)


def test_log_with_empty_kwargs():
    """Test that logging works with no additional kwargs"""
    log_debug("Simple message")
    log_info("Simple message")
    log_warning("Simple message")
    log_error("Simple message")
    log_critical("Simple message")
