"""Unit tests for Telegram security utilities."""

from app.integrations.telegram.security import verify_telegram_secret


def test_verify_telegram_secret_missing_header():
    """Test verification with missing header."""
    assert not verify_telegram_secret(None, "expected_secret")


def test_verify_telegram_secret_wrong_secret():
    """Test verification with wrong secret."""
    assert not verify_telegram_secret("wrong_secret", "expected_secret")


def test_verify_telegram_secret_empty_secret():
    """Test verification with empty secret."""
    assert not verify_telegram_secret("", "expected_secret")


def test_verify_telegram_secret_correct_secret():
    """Test verification with correct secret."""
    assert verify_telegram_secret("correct_secret", "correct_secret")


def test_verify_telegram_secret_no_expected():
    """Test verification with no expected secret."""
    assert not verify_telegram_secret("any_secret", "")


def test_verify_telegram_secret_empty_expected():
    """Test verification with empty expected secret."""
    assert not verify_telegram_secret("any_secret", "")


def test_verify_telegram_secret_case_sensitive():
    """Test that verification is case sensitive."""
    assert not verify_telegram_secret("Secret", "secret")
    assert not verify_telegram_secret("secret", "Secret")
    assert verify_telegram_secret("Secret", "Secret")
