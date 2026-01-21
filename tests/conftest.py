# tests/conftest.py
pytest_plugins = "pytest_homeassistant_custom_component"

import pytest

@pytest.fixture(autouse=True)
def enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield