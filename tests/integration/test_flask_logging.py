"""
Tests for universal logging configuration in shared module.
"""
import unittest.mock as mock
import pytest
import os
import logging
import sys

# Import the function directly to test it without reloading the module
from shared import setup_universal_logging



@pytest.mark.parametrize("log_level,expected_level", [
    ('DEBUG', logging.DEBUG),
    ('INFO', logging.INFO),
    ('WARNING', logging.WARNING),
    ('ERROR', logging.ERROR),
    ('CRITICAL', logging.CRITICAL),
])

def test_logging_configuration_with_level(log_level, expected_level):
    """Test logging configuration with different log levels."""
    with mock.patch.dict(os.environ, {'SERVICE_LOG_LEVEL': log_level}):
        setup_universal_logging()
        
        root_logger = logging.getLogger()
        assert root_logger.getEffectiveLevel() == expected_level


def test_logging_fallback_without_env_var():
    """Test logging fallback when no environment variable is set."""
    with mock.patch.dict(os.environ, {}, clear=True):
        setup_universal_logging()
        
        # Should default to DEBUG
        root_logger = logging.getLogger()
        assert root_logger.getEffectiveLevel() == logging.DEBUG


def test_logging_invalid_level_fallback():
    """Test logging fallback when invalid log level is provided."""
    with mock.patch.dict(os.environ, {'SERVICE_LOG_LEVEL': 'INVALID_LEVEL'}):
        setup_universal_logging()
        
        # Should fallback to DEBUG (default, consistent with missing env var)
        root_logger = logging.getLogger()
        assert root_logger.getEffectiveLevel() == logging.DEBUG


def test_logger_inherits_from_root():
    """Test that child loggers inherit from root logger configuration."""
    setup_universal_logging()
    
    # Create a child logger
    child_logger = logging.getLogger('autonotion.notion_registry_daily_plan')
    
    # Verify it inherits from root (effective level should match root)
    root_logger = logging.getLogger()
    assert child_logger.getEffectiveLevel() == root_logger.getEffectiveLevel()
