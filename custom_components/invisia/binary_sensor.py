from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_INSTALLATION_ID, CONF_CHARGING_STATION_ID


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    installation_id = entry.data[CONF_INSTALLATION_ID]
    cs_id = entry.data.get(CONF_CHARGING_STATION_ID)

    # If no charging station id configured, don't create entities
    if not cs_id:
        return

    async_add_entities([InvisiaCarPluggedIn(coordinator, installation_id, cs_id)])


class InvisiaCarPluggedIn(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, installation_id: str, cs_id: str):
        super().__init__(coordinator)
        self._installation_id = str(installation_id)
        self._cs_id = str(cs_id)

        self._attr_name = "Car plugged in"
        self._attr_unique_id = f"invisia_{self._installation_id}_cs_{self._cs_id}_plugged_in"
        self._attr_suggested_object_id = f"{DOMAIN}_charging_station_{coordinator.charging_station_id}_car_plugged_in"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self._installation_id}_cs_{self._cs_id}")},
            name=f"Invisia Charging Station {self._cs_id}",
            manufacturer="Invisia",
            model="Charging Station",
        )

    @property
    def is_on(self) -> bool:
        # Prefer RFID status (it actually reports carPluggedIn/charging), because
        # charging-station endpoints often return nulls for this field.
        cs = (self.coordinator.data or {}).get('status', {}).get('charging_status')
        if isinstance(cs, str) and cs:
            cs_l = cs.lower()
            return cs_l in ('carpluggedin', 'charging')

        # Fallback to charging-station detail if present
        st = (self.coordinator.data or {}).get('charging_station_detail', {}).get('status', {})
        return bool(st) and bool(st.get('car_plugged_in'))
    @property
    def extra_state_attributes(self):
        detail = (self.coordinator.data or {}).get("charging_station_detail") or {}
        status = detail.get("status") or {}
        return {
            "charging_status": status.get("charging_status"),
            "charging_mode": status.get("charging_mode"),
            "soc": status.get("soc"),
            "a_max": status.get("a_max"),
            "ladekabel": status.get("ladekabel"),
            "ip": status.get("ipadresse"),
        }
