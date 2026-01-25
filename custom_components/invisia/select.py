from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import InvisiaCoordinator

OPTIONS = ["instant", "optimized", "disabled"]


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: InvisiaCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([InvisiaChargingModeSelect(coordinator, entry.entry_id)])


class InvisiaChargingModeSelect(CoordinatorEntity[InvisiaCoordinator], SelectEntity):
    _attr_has_entity_name = True
    _attr_name = "Charging Mode"
    _attr_icon = "mdi:ev-station"
    _attr_options = OPTIONS

    def __init__(self, coordinator: InvisiaCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_suggested_object_id = "invisia_charging_mode"
        self._attr_unique_id = f"invisia_{entry.entry_id}_charging_mode"

    @property
    def current_option(self) -> str | None:
        data = self.coordinator.data or {}
        # Prefer charging station status, else RFID profile, else status block
        cs = data.get("charging_station_detail") or {}
        cs_status = cs.get("status", {}) if isinstance(cs, dict) else {}
        mode = cs_status.get("charging_mode")

        if not mode:
            rfid = data.get("rfid") or {}
            mode = rfid.get("profile")

        if not mode:
            status = data.get("status") or {}
            mode = status.get("charging_mode")

        mode = (mode or "").lower()
        return mode if mode in OPTIONS else None

    async def async_select_option(self, option: str) -> None:
        option = option.lower()
        if option not in OPTIONS:
            return
        await self.coordinator.api.set_rfid_profile(self.coordinator.ids.rfid_id, option)
        await self.coordinator.async_request_refresh()