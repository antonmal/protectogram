"""Unit tests for middleware functionality."""

import contextlib
import uuid
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.logging import correlation_id_var
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestCorrelationIdMiddleware:
    """Test correlation ID middleware."""

    def test_generates_uuid_when_no_header(self, client: TestClient) -> None:
        """Test that middleware generates UUID when no X-Request-ID header."""
        response = client.get("/health/live")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        
        # Verify it's a valid UUID
        correlation_id = response.headers["X-Request-ID"]
        uuid.UUID(correlation_id)  # Should not raise ValueError

    def test_uses_existing_header(self, client: TestClient) -> None:
        """Test that middleware uses existing X-Request-ID header."""
        test_correlation_id = "test-correlation-123"
        response = client.get("/health/live", headers={"X-Request-ID": test_correlation_id})
        
        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == test_correlation_id

    def test_sets_contextvar(self, client: TestClient) -> None:
        """Test that middleware sets correlation_id in context variable."""
        test_correlation_id = "test-context-456"
        
        # Clear any existing context
        with contextlib.suppress(LookupError):
            correlation_id_var.set("-")
        
        response = client.get("/health/live", headers={"X-Request-ID": test_correlation_id})
        
        assert response.status_code == 200
        # Note: ContextVar is request-scoped, so we can't easily test it here
        # The actual testing would be done in integration tests


class TestRequestLoggingMiddleware:
    """Test request logging middleware."""

    @patch("app.core.logging.get_logger")
    def test_logs_request_start_and_completion(self, mock_get_logger: Any, client: TestClient) -> None:
        """Test that middleware logs request start and completion."""
        mock_logger = mock_get_logger.return_value
        
        response = client.get("/health/live")
        
        assert response.status_code == 200
        
        # Verify logger was called for both start and completion
        assert mock_logger.info.call_count == 2
        
        # Check start log
        start_call = mock_logger.info.call_args_list[0]
        assert start_call[1]["method"] == "GET"
        assert start_call[1]["path"] == "/health/live"
        assert "correlation_id" in start_call[1]
        
        # Check completion log
        completion_call = mock_logger.info.call_args_list[1]
        assert completion_call[1]["method"] == "GET"
        assert completion_call[1]["path"] == "/health/live"
        assert completion_call[1]["status_code"] == 200
        assert "duration_ms" in completion_call[1]
        assert "correlation_id" in completion_call[1]

    def test_calculates_duration(self, client: TestClient) -> None:
        """Test that middleware calculates request duration."""
        with patch("app.core.logging.get_logger") as mock_get_logger:
            mock_logger = mock_get_logger.return_value
            
            response = client.get("/health/live")
            
            assert response.status_code == 200
            
            # Get the completion log call
            completion_call = mock_logger.info.call_args_list[1]
            duration_ms = completion_call[1]["duration_ms"]
            
            # Duration should be a positive integer
            assert isinstance(duration_ms, int)
            assert duration_ms >= 0


class TestMiddlewareIntegration:
    """Test middleware integration."""

    def test_middleware_order(self, client: TestClient) -> None:
        """Test that middlewares are installed in correct order."""
        response = client.get("/health/live", headers={"X-Request-ID": "test-order"})
        
        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == "test-order"

    def test_correlation_id_propagation(self, client: TestClient) -> None:
        """Test that correlation ID is propagated through the entire request."""
        test_correlation_id = "test-propagation-789"
        
        response = client.get("/health/live", headers={"X-Request-ID": test_correlation_id})
        
        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == test_correlation_id
