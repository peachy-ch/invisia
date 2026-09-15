from __future__ import annotations

from typing import Any

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
    def is_on(self) -> bool | None:
        # Prefer RFID status (it actually reports carPluggedIn/charging), because
        # charging-station endpoints often return nulls for this field.
        data = self.coordinator.data or {}

        status = data.get('status')
        charging_status = status.get('charging_status') if isinstance(status, dict) else None
        if isinstance(charging_status, str) and charging_status:
            return charging_status.lower() in ('carpluggedin', 'charging')

        # Fallback to charging-station detail if present
        detail = data.get('charging_station_detail')
        st = detail.get('status') if isinstance(detail, dict) else None
        if isinstance(st, dict) and st.get('car_plugged_in') is not None:
            return bool(st['car_plugged_in'])

        # Neither source reported anything. Unknown, not a confident "off".
        return None

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}

        detail = data.get("charging_station_detail")
        cs_status = detail.get("status") if isinstance(detail, dict) else None
        cs_status = cs_status if isinstance(cs_status, dict) else {}

        # RFID-only installations have no charging station, so the detail block is
        # empty and every attribute below would be dropped. The RFID status block
        # carries the same fields for them.
        _status = data.get("status")
        status = _status if isinstance(_status, dict) else {}

        def pick(key: str) -> Any:
            val = cs_status.get(key)
            return val if val is not None else status.get(key)

        return {
            "charging_status": pick("charging_status"),
            "charging_mode": pick("charging_mode"),
            "soc": pick("soc"),
            "a_max": pick("a_max"),
            "ladekabel": pick("ladekabel"),
            "ip": pick("ipadresse"),
        }
