"""DataUpdateCoordinator for the Cudy Router integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_SCAN_INTERVAL = 15


class CudyRouterDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage fetching data from the Cudy router."""

    def __init__(self, hass, entry, api) -> None:
        """Initialize the coordinator."""
        # Host is required by tests
        self.host = entry.data.get(CONF_HOST)

        # Scan interval: option > default
        update_interval = timedelta(
            seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )

        # IMPORTANT:
        # Do NOT set self.update_interval manually before super().__init__.
        # DataUpdateCoordinator defines it internally.
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} - {self.host}",
            update_interval=update_interval,
        )

        # Store references explicitly (tests assert on these)
        # NOTE: DataUpdateCoordinator sets self.hass and may set/overwrite self.config_entry,
        # so set these AFTER super().__init__.
        self.config_entry = entry
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the router via the API."""
        try:
            return await self.api.get_data(
                self.hass,
                self.config_entry.options,
                self.data,
            )
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Cudy router: {err}") from err