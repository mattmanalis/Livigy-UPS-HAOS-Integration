"""Sensor platform for Livigy UPS."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SENSOR_DESCRIPTIONS
from .entity import LivigyUpsCoordinatorEntity

UNIT_MAP = {
    "%": PERCENTAGE,
    "V": UnitOfElectricPotential.VOLT,
    "A": UnitOfElectricCurrent.AMPERE,
    "Hz": UnitOfFrequency.HERTZ,
    "W": UnitOfPower.WATT,
    "°C": UnitOfTemperature.CELSIUS,
}
TEXT_SENSOR_KEYS = {"company", "model", "firmware", "ups_mode", "ups_topology", "protocol_family", "status_summary"}
VALUE_LABELS = {
    "ups_mode": {
        "power_on": "Power On",
        "standby": "Standby",
        "bypass": "Bypass",
        "line": "Line",
        "battery": "Battery",
        "battery_test": "Battery Test",
        "fault": "Fault",
        "eco": "ECO",
        "converter": "Converter",
        "shutdown": "Shutdown",
    },
    "ups_topology": {
        "standby": "Standby",
        "line_interactive": "Line Interactive",
        "online": "Online",
        "unknown": "Unknown",
    },
    "protocol_family": {
        "centurion": "Centurion",
        "megatec": "Megatec",
        "unknown": "Unknown",
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        LivigyUpsSensor(coordinator, entry.entry_id, entry.data["host"], key, meta)
        for key, meta in SENSOR_DESCRIPTIONS.items()
    ]
    async_add_entities(entities)


class LivigyUpsSensor(LivigyUpsCoordinatorEntity, SensorEntity):
    """Represents a single Livigy UPS numeric/text sensor."""

    def __init__(self, coordinator, entry_id: str, host: str, key: str, meta: dict[str, str]) -> None:
        super().__init__(coordinator, entry_id, host)
        self._key = key
        self._attr_name = meta["name"]
        self._attr_unique_id = f"{entry_id}_{key}"

        native_unit = meta.get("native_unit")
        if native_unit:
            self._attr_native_unit_of_measurement = UNIT_MAP.get(native_unit, native_unit)

        device_class = meta.get("device_class")
        if device_class:
            self._attr_device_class = SensorDeviceClass(device_class)

        if key not in TEXT_SENSOR_KEYS:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        if self._key in VALUE_LABELS:
            value = data.get(self._key)
            if value is None:
                return None
            value_str = str(value).strip().lower()
            return VALUE_LABELS[self._key].get(value_str, str(value))
        if self._key == "estimated_load_watts":
            load_percent = data.get("load_percent")
            rated_watts = data.get("rated_watts")
            if load_percent is None:
                return None
            try:
                if rated_watts is not None:
                    return round(float(rated_watts) * float(load_percent) / 100.0, 1)

                rated_voltage = data.get("rated_voltage")
                rated_current = data.get("rated_current")
                if rated_voltage is None or rated_current is None:
                    return None
                # Fallback approximation based on apparent rated power and load percent.
                return round(float(rated_voltage) * float(rated_current) * float(load_percent) / 100.0, 1)
            except (TypeError, ValueError):
                return None
        return data.get(self._key)
