"""Sensor platform for Livigy UPS."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfFrequency, UnitOfTemperature
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
    "°C": UnitOfTemperature.CELSIUS,
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

        if key not in {"company", "model", "firmware"}:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)
