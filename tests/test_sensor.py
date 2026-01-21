"""Tests for the Cudy Router sensor platform."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.hass_cudy_router.const import (
    DOMAIN,
    MODULE_DEVICES,
    MODULE_SYSTEM,
    MODULE_WAN,
)
from custom_components.hass_cudy_router.coordinator import CudyRouterDataUpdateCoordinator
from custom_components.hass_cudy_router.sensor import (
    SENSOR_TYPES,
    CudyConnectedDevicesSensor,
    CudyGenericSensor,
    async_setup_entry,
)


def _get_description(key: str):
    for desc in SENSOR_TYPES:
        if desc.key == key:
            return desc
    raise AssertionError(f"Missing sensor description for key={key}")


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Create a config entry for the integration."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Cudy Router",
        data={"host": "router.gdzi.es"},
        options={},
        unique_id="router.gdzi.es",
    )


@pytest.fixture
def mock_api() -> AsyncMock:
    """Mocked API client used by the coordinator."""
    api = AsyncMock()
    api.get_data = AsyncMock(return_value={})
    return api


@pytest.fixture
def coordinator(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_api: AsyncMock
) -> CudyRouterDataUpdateCoordinator:
    """Create a coordinator instance safe for tests (passes config entry explicitly)."""
    config_entry.add_to_hass(hass)

    c = CudyRouterDataUpdateCoordinator(
        hass=hass,
        entry=config_entry,
        api=mock_api,
    )
    c.data = {}
    return c


@pytest.mark.asyncio
async def test_generic_sensor_native_value(hass: HomeAssistant, coordinator):
    """Generic sensors should extract native_value from coordinator data."""
    desc = _get_description("firmware_version")

    coordinator.data = {
        MODULE_SYSTEM: {
            "firmware": "1.2.3",
            "uptime": "00:01:00",
        }
    }

    entity = CudyGenericSensor(coordinator, desc)

    assert entity.native_value == "1.2.3"


@pytest.mark.asyncio
async def test_generic_sensor_handles_missing_module_data(hass: HomeAssistant, coordinator):
    """Generic sensors should return None if module data is missing or invalid."""
    desc = _get_description("firmware_version")
    entity = CudyGenericSensor(coordinator, desc)

    # No MODULE_SYSTEM present
    coordinator.data = {MODULE_WAN: {"wan_ip": "1.2.3.4"}}
    assert entity.native_value is None

    # MODULE_SYSTEM present, but not a dict
    coordinator.data = {MODULE_SYSTEM: "not-a-dict"}
    assert entity.native_value is None


@pytest.mark.asyncio
async def test_generic_sensor_unique_id_and_device_info(hass: HomeAssistant, coordinator):
    """Ensure unique_id and device_info are stable and correct."""
    desc = _get_description("firmware_version")
    entity = CudyGenericSensor(coordinator, desc)

    assert entity.unique_id == f"cudy_{coordinator.host}_{desc.key}"

    device_info = entity.device_info
    assert device_info is not None
    assert (DOMAIN, coordinator.host) in device_info["identifiers"]
    assert device_info["manufacturer"] == "Cudy"


@pytest.mark.asyncio
async def test_connected_devices_sensor_list_value_and_attrs(hass: HomeAssistant, coordinator):
    """Connected devices sensor: state is count, attributes expose details."""
    entity = CudyConnectedDevicesSensor(coordinator)

    coordinator.data = {
        MODULE_DEVICES: {
            "connected_devices": {
                "value": [
                    {"name": "Phone", "mac": "AA:BB:CC"},
                    {"name": "Laptop", "mac": "11:22:33"},
                ],
                "attributes": {
                    "devices": [
                        {"name": "Phone", "mac": "AA:BB:CC"},
                        {"name": "Laptop", "mac": "11:22:33"},
                    ]
                },
            }
        }
    }

    assert entity.native_value == 2
    assert entity.extra_state_attributes == {
        "devices": [
            {"name": "Phone", "mac": "AA:BB:CC"},
            {"name": "Laptop", "mac": "11:22:33"},
        ]
    }


@pytest.mark.asyncio
async def test_connected_devices_sensor_numeric_value(hass: HomeAssistant, coordinator):
    """If API returns a numeric value for connected_devices, use it directly."""
    entity = CudyConnectedDevicesSensor(coordinator)

    coordinator.data = {
        MODULE_DEVICES: {
            "connected_devices": {
                "value": 7,
                "attributes": {"devices": []},
            }
        }
    }

    assert entity.native_value == 7


@pytest.mark.asyncio
async def test_async_setup_entry_adds_all_entities(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    coordinator: CudyRouterDataUpdateCoordinator,
):
    """async_setup_entry should add len(SENSOR_TYPES) + 1 entities."""
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = coordinator

    added: list[Any] = []

    def _add_entities(entities):
        added.extend(entities)

    await async_setup_entry(hass, config_entry, _add_entities)

    assert len(added) == len(SENSOR_TYPES) + 1
    assert any(isinstance(e, CudyConnectedDevicesSensor) for e in added)
    assert sum(isinstance(e, CudyGenericSensor) for e in added) == len(SENSOR_TYPES)

    for entity in added:
        assert entity.unique_id