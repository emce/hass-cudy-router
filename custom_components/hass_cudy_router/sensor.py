"""Sensor platform for Cudy Router."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import *
from .coordinator import CudyRouterDataUpdateCoordinator

def _value_or_dict_value(v: Any) -> Any:
    if isinstance(v, dict):
        return v.get("value")
    return v


@dataclass(frozen=True, kw_only=True)
class CudySensorEntityDescription(SensorEntityDescription):

    module: str
    value_fn: Callable[[dict[str, Any]], Any]


SENSOR_TYPES: tuple[CudySensorEntityDescription, ...] = (
    # ----- SYSTEM -----
    CudySensorEntityDescription(
        key=SENSOR_FIRMWARE_VERSION,
        name="Firmware Version",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_SYSTEM,
        value_fn=lambda data: data.get(SENSOR_FIRMWARE_VERSION),
    ),
    CudySensorEntityDescription(
        key=SENSOR_HARDWARE,
        name="Hardware",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_SYSTEM,
        value_fn=lambda data: data.get(SENSOR_HARDWARE),
    ),
    CudySensorEntityDescription(
        key=SENSOR_SYSTEM_UPTIME,
        name="Connected Time",
        icon="mdi:clock-check",
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_SYSTEM,
        value_fn=lambda data: data.get(SENSOR_SYSTEM_UPTIME),
    ),
    # ----- MESH -----
    CudySensorEntityDescription(
        key=SENSOR_MESH_NETWORK,
        name="Mesh Network",
        icon="mdi:router-network-wireless",
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_MESH,
        value_fn=lambda data: data.get(SENSOR_MESH_NETWORK),
    ),
    CudySensorEntityDescription(
        key=SENSOR_MESH_UNITS,
        name="Mesh Units",
        icon="mdi:devices",
        state_class=SensorStateClass.MEASUREMENT,
        module=MODULE_SYSTEM,
        value_fn=lambda data: data.get(SENSOR_MESH_UNITS),
    ),
    # ----- WAN -----
    CudySensorEntityDescription(
        key=SENSOR_WAN_PUBLIC_IP,
        name="WAN Public IP Address",
        icon="mdi:earth",
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_WAN,
        value_fn=lambda data: data.get(SENSOR_WAN_PUBLIC_IP),
    ),
    CudySensorEntityDescription(
        key=SENSOR_WAN_IP,
        name="WAN IP Address",
        icon="mdi:ip-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_WAN,
        value_fn=lambda data: data.get(SENSOR_WAN_IP),
    ),
    CudySensorEntityDescription(
        key=SENSOR_WAN_DNS,
        name="WAN DNS Address(es)",
        icon="mdi:dns",
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_WAN,
        value_fn=lambda data: data.get(SENSOR_WAN_DNS),
    ),
    CudySensorEntityDescription(
        key=SENSOR_WAN_TYPE,
        name="Connection Type",
        icon="mdi:transit-connection-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_WAN,
        value_fn=lambda data: data.get(SENSOR_WAN_TYPE),
    ),
    CudySensorEntityDescription(
        key=SENSOR_WAN_UPTIME,
        name="WAN Connected Time",
        icon="mdi:clock-check",
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_WAN,
        value_fn=lambda data: data.get(SENSOR_WAN_UPTIME),
    ),
    # ----- LAN -----
    CudySensorEntityDescription(
        key=SENSOR_LAN_IP,
        name="LAN IP Address",
        icon="mdi:ip-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        module=MODULE_LAN,
        value_fn=lambda data: data.get(SENSOR_LAN_IP),
    ),
    # ----- DEVICES COUNTS -----
    CudySensorEntityDescription(
        key=SENSOR_DEVICE_COUNT,
        name="Total Devices Connected",
        icon="mdi:devices",
        state_class=SensorStateClass.MEASUREMENT,
        module=MODULE_DEVICES,
        value_fn=lambda data: _value_or_dict_value(data.get(SENSOR_DEVICE_COUNT)),
    ),
    CudySensorEntityDescription(
        key=SENSOR_WIFI_24_DEVICE_COUNT,
        name="2.4GHz WiFi Devices Connected",
        icon="mdi:wifi",
        state_class=SensorStateClass.MEASUREMENT,
        module=MODULE_DEVICES,
        value_fn=lambda data: _value_or_dict_value(data.get(SENSOR_WIFI_24_DEVICE_COUNT)),
    ),
    CudySensorEntityDescription(
        key=SENSOR_WIFI_5_DEVICE_COUNT,
        name="5GHz WiFi Devices Connected",
        icon="mdi:wifi",
        state_class=SensorStateClass.MEASUREMENT,
        module=MODULE_DEVICES,
        value_fn=lambda data: _value_or_dict_value(data.get(SENSOR_WIFI_5_DEVICE_COUNT)),
    ),
    CudySensorEntityDescription(
        key=SENSOR_WIRED_DEVICE_COUNT,
        name="Wired Devices Connected",
        icon="mdi:lan",
        state_class=SensorStateClass.MEASUREMENT,
        module=MODULE_DEVICES,
        value_fn=lambda data: _value_or_dict_value(data.get(SENSOR_WIRED_DEVICE_COUNT)),
    ),
    CudySensorEntityDescription(
        key=SENSOR_MESH_DEVICE_COUNT,
        name="Mesh Devices Connected",
        icon="mdi:router-network",
        state_class=SensorStateClass.MEASUREMENT,
        module=MODULE_DEVICES,
        value_fn=lambda data: _value_or_dict_value(data.get(SENSOR_MESH_DEVICE_COUNT)),
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