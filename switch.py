from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_INSTALLATION_ID, CONF_RFID_ID


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]

    installation_id = entry.data[CONF_INSTALLATION_ID]
    rfid_id = entry.data[CONF_RFID_ID]

    async_add_entities([InvisiaOptimizedSwitch(coordinator, api, installation_id, rfid_id)])


class InvisiaOptimizedSwitch(CoordinatorEntity, SwitchEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, api, installation_id: str, rfid_id: str):
        super().__init__(coordinator)
        self.api = api
        self._installation_id = str(installation_id)
        self._rfid_id = str(rfid_id)

        self._attr_name = "Optimized charging"
        self._attr_unique_id = f"invisia_{self._installation_id}_{self._rfid_id}_optimized"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self._installation_id}_{self._rfid_id}")},
            name=f"Invisia RFID {self._rfid_id}",
            manufacturer="Invisia",
            model="RFID",
        )

    @property
    def is_on(self) -> bool:
        payload = (self.coordinator.data or {}).get("rfid_status", {})
        rfid = payload.get("rfid") if isinstance(payload, dict) else None
        if not isinstance(rfid, dict):
            rfid = payload if isinstance(payload, dict) else {}

        return rfid.get("profile") == "optimized"

    async def async_turn_on(self, **kwargs) -> None:
        await self.api.set_rfid_profile(self._rfid_id, "optimized")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.api.set_rfid_profile(self._rfid_id, "instant")
        await self.coordinator.async_request_refresh()