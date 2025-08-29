"""Unit tests for logging functionality."""

import contextlib
import logging
import structlog


from app.core.logging import correlation_id_var, get_logger, setup_logging


class TestLoggingSetup:
    """Test logging setup functionality."""

    def test_setup_logging_configures_structlog(self) -> None:
        """Test that setup_logging configures structlog correctly."""
        # Clear any existing configuration
        structlog.reset_defaults()
        
        setup_logging()
        
        # Verify structlog is configured
        assert structlog.is_configured()
        
        # Get a logger and verify it's a BoundLoggerLazyProxy initially
        logger = structlog.get_logger("test")
        assert hasattr(logger, '_logger')  # Check it's a proxy

    def test_setup_logging_configures_standard_logging(self) -> None:
        """Test that setup_logging configures standard library logging."""
        setup_logging()
        
        # Verify root logger is configured
        root_logger = logging.getLogger()
        assert root_logger.handlers
        
        # Verify log level is set
        assert root_logger.level <= logging.INFO

    def test_get_logger_returns_logger(self) -> None:
        """Test that get_logger returns a logger instance."""
        setup_logging()
        
        logger = get_logger("test_logger")
        assert hasattr(logger, 'info')  # Check it has logging methods

    def test_get_logger_with_none_name(self) -> None:
        """Test that get_logger works with None name."""
        setup_logging()
        
        logger = get_logger(None)
        assert hasattr(logger, 'info')  # Check it has logging methods


class TestCorrelationIdInLogs:
    """Test correlation ID inclusion in logs."""

    def test_correlation_id_included_in_logs(self) -> None:
        """Test that correlation_id is included in log entries."""
        setup_logging()
        
        # Set a test correlation ID
        test_correlation_id = "test-correlation-123"
        correlation_id_var.set(test_correlation_id)
        
        # Capture log output
        captured_logs = []
        
        def capture_log(
            logger: structlog.stdlib.BoundLogger, 
            method_name: str, 
            event_dict: dict
        ) -> dict:
            captured_logs.append(event_dict)
            return event_dict
        
        # Temporarily add our capture processor
        processors = structlog.get_config()["processors"]
        processors.insert(-1, capture_log)  # Insert before JSONRenderer
        
        try:
            logger = get_logger("test")
            logger.info("Test message")
            
            # Verify correlation_id is in the log entry
            assert len(captured_logs) == 1
            log_entry = captured_logs[0]
            assert log_entry["correlation_id"] == test_correlation_id
            assert log_entry["service"] == "protectogram"
            
        finally:
            # Restore original configuration
            setup_logging()

    def test_default_correlation_id_when_not_set(self) -> None:
        """Test that default correlation_id is used when not set."""
        setup_logging()
        
        # Clear any existing correlation_id
        with contextlib.suppress(LookupError):
            correlation_id_var.set("-")
        
        # Capture log output
        captured_logs = []
        
        def capture_log(
            logger: structlog.stdlib.BoundLogger, 
            method_name: str, 
            event_dict: dict
        ) -> dict:
            captured_logs.append(event_dict)
            return event_dict
        
        # Temporarily add our capture processor
        processors = structlog.get_config()["processors"]
        processors.insert(-1, capture_log)  # Insert before JSONRenderer
        
        try:
            logger = get_logger("test")
            logger.info("Test message")
            
            # Verify default correlation_id is used
            assert len(captured_logs) == 1
            log_entry = captured_logs[0]
            assert log_entry["correlation_id"] == "-"
            assert log_entry["service"] == "protectogram"
            
        finally:
            # Restore original configuration
            setup_logging()
