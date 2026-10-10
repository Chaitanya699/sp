"""Pytest configuration for NIM Sentinel tests."""

from dotenv import load_dotenv

# Load .env file for all tests
load_dotenv()


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "eval: Evaluation tests")
    config.addinivalue_line("markers", "redteam: Red team tests")
