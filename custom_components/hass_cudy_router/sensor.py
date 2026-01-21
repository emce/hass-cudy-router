"""Sensor platform for Cudy Router."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfDataRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MODULE_DEVICES,
    MODULE_LAN,
    MODULE_MESH,
    MODULE_SYSTEM,
    MODULE_WAN,
)
from .coordinator import CudyRouterDataUpdateCoordinator


# Home Assistant pattern: extend SensorEntityDescription to add integration-specific fields.
# Use kw_only=True so our extra fields must be passed as keywords.
@dataclass(frozen=True, kw_only=True)
class CudySensorEntityDescription(SensorEntityDescription):
    """Describes a Cudy Router sensor."""

    module: str
    value_fn: Callable[[dict[str, Any]], Any]


SENSOR_TYPES: tuple[CudySensorEntityDescription, ...] = (
    # ----- SYSTEM -----
    CudySensorEntityDescription(
        key="firmware_version",
        name="Firmware Version",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_SYSTEM,
        value_fn=lambda data: data.get("firmware"),
    ),
    CudySensorEntityDescription(
        key="system_uptime",
        name="Connected Time",
        icon="mdi:clock-check",
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_SYSTEM,
        value_fn=lambda data: data.get("uptime"),
    ),
    # ----- MESH -----
    CudySensorEntityDescription(
        key="mesh_network",
        name="Mesh Network",
        icon="mdi:router-network-wireless",
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_MESH,
        value_fn=lambda data: data.get("mesh_network"),
    ),
    CudySensorEntityDescription(
        key="mesh_units",
        name="Mesh Units",
        icon="mdi:devices",
        state_class=SensorStateClass.MEASUREMENT,
        module=MODULE_SYSTEM,
        value_fn=lambda data: (data.get("mesh_units") or {}).get("value"),
    ),
    # ----- WAN -----
    CudySensorEntityDescription(
        key="wan_public_ip",
        name="WAN Public IP Address",
        icon="mdi:earth",
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_WAN,
        value_fn=lambda data: data.get("wan_public_ip"),
    ),
    CudySensorEntityDescription(
        key="wan_ip",
        name="WAN IP Address",
        icon="mdi:ip-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_WAN,
        value_fn=lambda data: data.get("wan_ip"),
    ),
    CudySensorEntityDescription(
        key="wan_dns",
        name="WAN DNS Address(es)",
        icon="mdi:dns",
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_WAN,
        value_fn=lambda data: data.get("wan_dns"),
    ),
    CudySensorEntityDescription(
        key="wan_type",
        name="Connection Type",
        icon="mdi:transit-connection-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_WAN,
        value_fn=lambda data: data.get("wan_type"),
    ),
    CudySensorEntityDescription(
        key="wan_uptime",
        name="WAN Connected Time",
        icon="mdi:clock-check",
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_WAN,
        value_fn=lambda data: data.get("wan_uptime"),
    ),
    # Real-time throughput if your API returns it (Mbps)
    # Expected keys:
    #   coordinator.data[MODULE_WAN]["download_speed_mbps"] -> float
    #   coordinator.data[MODULE_WAN]["upload_speed_mbps"] -> float
    CudySensorEntityDescription(
        key="wan_download_speed",
        name="WAN Download Speed",
        icon="mdi:download-network",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_WAN,
        value_fn=lambda data: data.get("download_speed_mbps"),
    ),
    CudySensorEntityDescription(
        key="wan_upload_speed",
        name="WAN Upload Speed",
        icon="mdi:upload-network",
        device_class=SensorDeviceClass.DATA_RATE,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_WAN,
        value_fn=lambda data: data.get("upload_speed_mbps"),
    ),
    # ----- LAN -----
    CudySensorEntityDescription(
        key="lan_ip",
        name="LAN IP Address",
        icon="mdi:ip-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_LAN,
        value_fn=lambda data: data.get("lan_ip"),
    ),
    # ----- DEVICES COUNTS -----
    CudySensorEntityDescription(
        key="device_count",
        name="Total Devices Connected",
        icon="mdi:devices",
        state_class=SensorStateClass.MEASUREMENT,
        module=MODULE_DEVICES,
        value_fn=lambda data: (data.get("device_count") or {}).get("value"),
    ),
    CudySensorEntityDescription(
        key="wifi_24_device_count",
        name="2.4GHz WiFi Devices Connected",
        icon="mdi:wifi",
        state_class=SensorStateClass.MEASUREMENT,
        module=MODULE_DEVICES,
        value_fn=lambda data: (data.get("wifi_24_device_count") or {}).get("value"),
    ),
    CudySensorEntityDescription(
        key="wifi_5_device_count",
        name="5GHz WiFi Devices Connected",
        icon="mdi:wifi",
        state_class=SensorStateClass.MEASUREMENT,
        module=MODULE_DEVICES,
        value_fn=lambda data: (data.get("wifi_5_device_count") or {}).get("value"),
    ),
    CudySensorEntityDescription(
        key="wired_device_count",
        name="Wired Devices Connected",
        icon="mdi:lan",
        state_class=SensorStateClass.MEASUREMENT,
        module=MODULE_DEVICES,
        value_fn=lambda data: (data.get("wired_device_count") or {}).get("value"),
    ),
    CudySensorEntityDescription(
        key="mesh_device_count",
        name="Mesh Devices Connected",
        icon="mdi:router-network",
        state_class=SensorStateClass.MEASUREMENT,
        module=MODULE_DEVICES,
        value_fn=lambda data: (data.get("mesh_device_count") or {}).get("value"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cudy Router sensors from a config entry."""
    coordinator: CudyRouterDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        CudyGenericSensor(coordinator, description) for description in SENSOR_TYPES
    ]

    # A dedicated sensor that exposes the *count* as state and the device list as attributes.
    entities.append(CudyConnectedDevicesSensor(coordinator))

    async_add_entities(entities)


class CudyBaseEntity(CoordinatorEntity[CudyRouterDataUpdateCoordinator]):
    """Base entity to ensure consistent device_info for all entities."""

    def __init__(self, coordinator: CudyRouterDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Cudy Router {coordinator.host}",
            "manufacturer": "Cudy",
        }


class CudyGenericSensor(CudyBaseEntity, SensorEntity):
    """A coordinator-driven sensor defined by a description."""

    entity_description: CudySensorEntityDescription

    def __init__(
        self,
        coordinator: CudyRouterDataUpdateCoordinator,
        description: CudySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description

        self._attr_unique_id = f"cudy_{coordinator.host}_{description.key}"
        self._attr_name = description.name

    @property
    def native_value(self) -> Any:
        module_data = (self.coordinator.data or {}).get(self.entity_description.module)
        if not isinstance(module_data, dict):
            return None
        try:
            return self.entity_description.value_fn(module_data)
        except Exception:
            return None


class CudyConnectedDevicesSensor(CudyBaseEntity, SensorEntity):
    """Connected devices list exposed via attributes; state is device count."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:account-network"
    _attr_name = "Connected Devices"

    def __init__(self, coordinator: CudyRouterDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"cudy_{coordinator.host}_connected_devices"

    @property
    def native_value(self) -> Any:
        devices = (
            (self.coordinator.data or {})
            .get(MODULE_DEVICES, {})
            .get("connected_devices", {})
            .get("value")
        )

        if isinstance(devices, list):
            return len(devices)

        if isinstance(devices, (int, float)):
            return devices

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = (
            (self.coordinator.data or {})
            .get(MODULE_DEVICES, {})
            .get("connected_devices", {})
            .get("attributes")
        )
        return attrs if isinstance(attrs, dict) else {}