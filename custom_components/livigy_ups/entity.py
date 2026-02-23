"""Entity helpers for Livigy UPS."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import LivigyUpsCoordinator


class LivigyUpsCoordinatorEntity(CoordinatorEntity[LivigyUpsCoordinator]):
    """Base entity class with shared device info."""

    def __init__(self, coordinator: LivigyUpsCoordinator, entry_id: str, host: str) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._host = host

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={("livigy_ups", self._entry_id)},
            name="Livigy UPS",
            manufacturer=str(self.coordinator.data.get("company") or "Livigy / PowerShield"),
            model=str(self.coordinator.data.get("model") or "Unknown"),
            sw_version=str(self.coordinator.data.get("firmware") or "Unknown"),
            configuration_url=f"http://{self._host}",
        )
