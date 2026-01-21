# tests/test_coordinator.py

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL, CONF_PROTOCOL, CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hass_cudy_router.const import DOMAIN
from custom_components.hass_cudy_router.coordinator import (
    CudyRouterDataUpdateCoordinator,
)
from custom_components.hass_cudy_router.router import CudyRouter


@pytest.fixture
def mock_api() -> CudyRouter:
    """Return a mocked CudyRouter."""
    api = MagicMock(spec=CudyRouter)
    api.get_data = AsyncMock()
    return api


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "router.gdzi.es", CONF_PROTOCOL: "https", CONF_USERNAME: "admin", CONF_PASSWORD: "3zUo2Fk@"},
        options={CONF_SCAN_INTERVAL: 30},
        title="Test Cudy Router",
    )


@pytest.mark.asyncio
async def test_coordinator_initialization(hass, config_entry, mock_api):
    """Coordinator should use host and scan interval from config entry."""
    config_entry.add_to_hass(hass)

    coordinator = CudyRouterDataUpdateCoordinator(
        hass=hass,
        entry=config_entry,
        api=mock_api,
    )

    assert coordinator.host == "router.gdzi.es"
    assert coordinator.update_interval == timedelta(seconds=30)
    assert coordinator.config_entry is config_entry
    assert coordinator.name == f"{DOMAIN} - router.gdzi.es"


@pytest.mark.asyncio
async def test_coordinator_uses_default_scan_interval(hass, mock_api):
    """If no scan_interval option is set, default to 15 seconds."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "router.gdzi.es"},
        options={},  # no CONF_SCAN_INTERVAL
    )
    entry.add_to_hass(hass)

    coordinator = CudyRouterDataUpdateCoordinator(hass, entry, mock_api)

    assert coordinator.update_interval == timedelta(seconds=15)


@pytest.mark.asyncio
async def test_async_update_data_success(hass, config_entry, mock_api):
    """_async_update_data should return data from api.get_data."""
    config_entry.add_to_hass(hass)

    previous_data: dict[str, Any] = {"old": "value"}

    coordinator = CudyRouterDataUpdateCoordinator(hass, config_entry, mock_api)
    coordinator.data = previous_data

    mock_api.get_data.return_value = {"new": "data"}

    result = await coordinator._async_update_data()

    assert result == {"new": "data"}

    mock_api.get_data.assert_awaited_once_with(
        hass,
        config_entry.options,
        previous_data,
    )


@pytest.mark.asyncio
async def test_async_update_data_failure_raises_updatefailed(
    hass, config_entry, mock_api
):
    """Any exception from api.get_data should be wrapped in UpdateFailed."""
    config_entry.add_to_hass(hass)

    coordinator = CudyRouterDataUpdateCoordinator(hass, config_entry, mock_api)

    mock_api.get_data.side_effect = RuntimeError("boom")

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()