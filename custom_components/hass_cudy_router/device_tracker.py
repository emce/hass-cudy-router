"""Device tracker platform for Cudy Router."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODULE_DEVICES, OPTIONS_DEVICELIST
from .coordinator import CudyRouterDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up device tracker entities from a config entry."""
    coordinator: CudyRouterDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    device_list = config_entry.options.get(OPTIONS_DEVICELIST, "")
    tracked_macs = [mac.strip().lower() for mac in device_list.split(",") if mac.strip()]

    async_add_entities(
        CudyRouterDeviceTracker(coordinator, mac) for mac in tracked_macs
    )


class CudyRouterDeviceTracker(
    CoordinatorEntity[CudyRouterDataUpdateCoordinator], TrackerEntity
):
    """Device tracker for a device connected to the Cudy Router."""

    _attr_source_type = SourceType.ROUTER
    _attr_should_poll = False

    def __init__(self, coordinator: CudyRouterDataUpdateCoordinator, mac: str) -> None:
        super().__init__(coordinator)
        self._mac = mac

        self._attr_unique_id = f"cudy_device_{mac.replace(':', '').replace('-', '')}"
        self._attr_name = f"Cudy Device {mac}"

        # Attach trackers to the router device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "manufacturer": "Cudy",
            "name": f"Cudy Router {coordinator.host}",
        }

    @property
    def available(self) -> bool:
        """Tracker is available if the coordinator is healthy."""
        return self.coordinator.last_update_success

    @property
    def is_connected(self) -> bool:
        """Return True if the device is currently connected."""
        devices = (
            (self.coordinator.data or {})
            .get(MODULE_DEVICES, {})
            .get("device_list", [])
        )

        for dev in devices:
            if not isinstance(dev, dict):
                continue

            if dev.get("mac", "").lower() != self._mac:
                continue

            connection = (dev.get("connection") or "").lower()
            signal = dev.get("signal")

            # Wired devices are always online
            if connection == "wired":
                return True

            # Wireless devices: valid signal means present
            if signal and str(signal).strip() not in ("", "---"):
                return True

            return False

        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose full device info as extra attributes."""
        devices = (
            (self.coordinator.data or {})
            .get(MODULE_DEVICES, {})
            .get("device_list", [])
        )

        for dev in devices:
            if isinstance(dev, dict) and dev.get("mac", "").lower() == self._mac:
                return dev.copy()

        return {}