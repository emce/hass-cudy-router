"""Sensor definitions for Cudy Router."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfDataRate, UnitOfInformation, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODULE_BANDWIDTH, MODULE_LAN, MODULE_SYSTEM, MODULE_DEVICES
from .coordinator import CudyRouterDataUpdateCoordinator

@dataclass
class CudySensorEntityDescription(SensorEntityDescription):
    module: str = None
    value_fn: Callable[[dict], Any] = None

SENSOR_TYPES: tuple[CudySensorEntityDescription, ...] = (
    # Bandwidth
    CudySensorEntityDescription(
        key="eth0_download_speed", name="Download Speed", module=MODULE_BANDWIDTH,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        device_class=SensorDeviceClass.DATA_RATE, state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:download-network", value_fn=lambda data: data.get("download_mbps"),
    ),
    CudySensorEntityDescription(
        key="eth0_upload_speed", name="Upload Speed", module=MODULE_BANDWIDTH,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        device_class=SensorDeviceClass.DATA_RATE, state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:upload-network", value_fn=lambda data: data.get("upload_mbps"),
    ),
    CudySensorEntityDescription(
        key="eth0_download_total", name="Download Total", module=MODULE_BANDWIDTH,
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE, state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:download-circle", value_fn=lambda data: data.get("download_total_gb"),
    ),
    CudySensorEntityDescription(
        key="eth0_upload_total", name="Upload Total", module=MODULE_BANDWIDTH,
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE, state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:upload-circle", value_fn=lambda data: data.get("upload_total_gb"),
    ),
    # System
    CudySensorEntityDescription(
        key="firmware_version", name="Firmware Version", module=MODULE_SYSTEM,
        icon="mdi:chip", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("firmware"),
    ),
    CudySensorEntityDescription(
        key="hardware_version", name="Hardware Version", module=MODULE_SYSTEM,
        icon="mdi:server", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("hardware"),
    ),
    # LAN
    CudySensorEntityDescription(
        key="lan_ip", name="LAN IP Address", module=MODULE_LAN,
        icon="mdi:ip-network", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("ip_address"),
    ),
    CudySensorEntityDescription(
        key="lan_uptime", name="Connected Time", module=MODULE_LAN,
        icon="mdi:clock-check", entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("connected_time"),
    ),
    # Devices
    CudySensorEntityDescription(
        key="top_downloader_hostname", name="Top Downloader", module=MODULE_DEVICES,
        icon="mdi:arrow-down-bold-circle",
        value_fn=lambda data: data.get("top_downloader_hostname", {}).get("value"),
    ),
    CudySensorEntityDescription(
        key="top_downloader_speed", name="Top Downloader Speed", module=MODULE_DEVICES,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        device_class=SensorDeviceClass.DATA_RATE, state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
        value_fn=lambda data: data.get("top_downloader_speed", {}).get("value"),
    ),
     CudySensorEntityDescription(
        key="top_uploader_hostname", name="Top Uploader", module=MODULE_DEVICES,
        icon="mdi:arrow-up-bold-circle",
        value_fn=lambda data: data.get("top_uploader_hostname", {}).get("value"),
    ),
    CudySensorEntityDescription(
        key="top_uploader_speed", name="Top Uploader Speed", module=MODULE_DEVICES,
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        device_class=SensorDeviceClass.DATA_RATE, state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
        value_fn=lambda data: data.get("top_uploader_speed", {}).get("value"),
    ),
    CudySensorEntityDescription(
        key="device_count", name="Device Count", module=MODULE_DEVICES,
        state_class=SensorStateClass.MEASUREMENT, icon="mdi:devices",
        value_fn=lambda data: data.get("device_count", {}).get("value"),
    ),
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: CudyRouterDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = []
    for description in SENSOR_TYPES:
        sensors.append(CudyGenericSensor(coordinator, description))
    sensors.append(CudyConnectedDevicesSensor(coordinator))
    async_add_entities(sensors)

class CudyGenericSensor(CoordinatorEntity, SensorEntity):
    entity_description: CudySensorEntityDescription

    def __init__(self, coordinator: CudyRouterDataUpdateCoordinator, description: CudySensorEntityDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.host}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Cudy Router {coordinator.host}",
            "manufacturer": "Cudy",
        }

    @property
    def native_value(self) -> Any:
        module_data = self.coordinator.data.get(self.entity_description.module)
        if not module_data: return None
        return self.entity_description.value_fn(module_data)

class CudyConnectedDevicesSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: CudyRouterDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.host}_connected_devices"
        self._attr_name = "Connected Devices"
        self._attr_icon = "mdi:lan-connect"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.host)},
            "name": f"Cudy Router {coordinator.host}",
        }

    @property
    def native_value(self):
        data = self.coordinator.data.get(MODULE_DEVICES, {})
        return data.get("connected_devices", {}).get("value")

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data.get(MODULE_DEVICES, {})
        return data.get("connected_devices", {}).get("attributes", {})
