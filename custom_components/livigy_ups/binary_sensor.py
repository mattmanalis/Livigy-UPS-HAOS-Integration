"""Binary sensors for Livigy UPS."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BINARY_SENSOR_DESCRIPTIONS, DOMAIN
from .entity import LivigyUpsCoordinatorEntity

PROBLEM_KEYS = {"utility_fail", "battery_low", "ups_failed"}
RUNNING_KEYS = {"test_in_progress", "shutdown_active"}
POWER_KEYS = {"avr_active"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        LivigyUpsBinarySensor(coordinator, entry.entry_id, entry.data["host"], key, name)
        for key, name in BINARY_SENSOR_DESCRIPTIONS.items()
    ]
    async_add_entities(entities)


class LivigyUpsBinarySensor(LivigyUpsCoordinatorEntity, BinarySensorEntity):
    """Represents Livigy UPS status bit sensors."""

    def __init__(self, coordinator, entry_id: str, host: str, key: str, name: str) -> None:
        super().__init__(coordinator, entry_id, host)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_{key}"

        if key in PROBLEM_KEYS:
            self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        elif key in RUNNING_KEYS:
            self._attr_device_class = BinarySensorDeviceClass.RUNNING
        elif key in POWER_KEYS:
            self._attr_device_class = BinarySensorDeviceClass.POWER

    @property
    def is_on(self) -> bool | None:
        value = (self.coordinator.data or {}).get(self._key)
        if value is None:
            return None
        return bool(value)
