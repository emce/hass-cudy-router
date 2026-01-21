"""The Cudy Router integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PROTOCOL,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN
from .coordinator import CudyRouterDataUpdateCoordinator
from .router import CudyRouter

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.DEVICE_TRACKER, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Cudy Router from a config entry."""

    data = entry.data
    api = CudyRouter(
        hass,
        data[CONF_PROTOCOL],
        data[CONF_HOST],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
    )

    coordinator = CudyRouterDataUpdateCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # -------- Service: cudy_router.reboot --------
    async def _handle_reboot(call: ServiceCall) -> None:
        """Handle service call to reboot the router."""
        entry_id = call.data.get("entry_id", entry.entry_id)
        coord = hass.data.get(DOMAIN, {}).get(entry_id)

        if coord is None:
            _LOGGER.error("No coordinator found for entry_id=%s", entry_id)
            return

        _LOGGER.warning("Rebooting Cudy router (%s)", coord.host)
        await coord.api.async_reboot(hass)

    if not hass.services.has_service(DOMAIN, "reboot"):
        hass.services.async_register(DOMAIN, "reboot", _handle_reboot)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            del hass.data[DOMAIN]

        if not hass.data.get(DOMAIN) and hass.services.has_service(DOMAIN, "reboot"):
            hass.services.async_remove(DOMAIN, "reboot")

    return unload_ok