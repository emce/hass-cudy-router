"""Button platform for Cudy Router."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

BUTTON_TYPES: tuple[ButtonEntityDescription, ...] = (
    ButtonEntityDescription(
        key="reboot",
        name="Reboot",
        icon="mdi:restart-alert",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cudy Router buttons based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CudyRouterButton(coordinator, entry, desc) for desc in BUTTON_TYPES])


class CudyRouterButton(CoordinatorEntity, ButtonEntity):
    """Representation of a Cudy Router button."""

    def __init__(self, coordinator, entry: ConfigEntry, description: ButtonEntityDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry

        # Unique per config entry (best practice)
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

        # Optional but nice: attach to the same device as sensors
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Cudy Router {coordinator.host}",
            "manufacturer": "Cudy",
        }

        # Name shown in UI (if you want it to include host)
        self._attr_name = f"Cudy Router {coordinator.host} {description.name}"

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.warning("Reboot button pressed for %s", self.coordinator.host)

        # Calls your router API
        await self.coordinator.api.async_reboot(self.hass)