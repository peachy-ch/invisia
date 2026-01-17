from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_INSTALLATION_ID, CONF_RFID_ID

SENSORS = [
    ("profile", "RFID Profile", None, None),
    ("current_power_flow", "RFID Power", "W", SensorDeviceClass.POWER),
    ("e_charged", "RFID Energy Charged", "kWh", SensorDeviceClass.ENERGY),
    ("status", "RFID Status", None, None),
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    installation_id = entry.data[CONF_INSTALLATION_ID]
    rfid_id = entry.data[CONF_RFID_ID]

    async_add_entities(
        InvisiaRfidSensor(coordinator, installation_id, rfid_id, key, name, unit, device_class)
        for key, name, unit, device_class in SENSORS
    )


class InvisiaRfidSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        installation_id: str,
        rfid_id: str,
        key: str,
        name: str,
        unit: str | None,
        device_class,
    ):
        super().__init__(coordinator)
        self._installation_id = str(installation_id)
        self._rfid_id = str(rfid_id)
        self._key = key

        self._attr_name = name
        self._attr_unique_id = f"invisia_{self._installation_id}_{self._rfid_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self._installation_id}_{self._rfid_id}")},
            name=f"Invisia RFID {self._rfid_id}",
            manufacturer="Invisia",
            model="RFID",
        )

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        payload = data.get("rfid_status", {})

        # Normalise: sometimes it's {rfid:{...}, stats:{...}}, sometimes it's the RFID itself
        rfid = payload.get("rfid") if isinstance(payload, dict) else None
        if not isinstance(rfid, dict):
            rfid = payload if isinstance(payload, dict) else {}

        stats = payload.get("stats", {}) if isinstance(payload, dict) else {}

        if self._key == "profile":
            return rfid.get("profile")

        if self._key == "status":
            # status is top-level on the wrapped payload; often null
            return payload.get("status") if isinstance(payload, dict) else None

        # power + energy come from stats
        return stats.get(self._key)

    @property
    def extra_state_attributes(self):
        # Only attach the big JSON blobs to ONE entity to avoid clutter/bloat.
        if self._key != "status":
            return None

        data = self.coordinator.data or {}
        cs_detail = data.get("charging_station_detail") or {}
        cs_status = (cs_detail.get("status") or {}) if isinstance(cs_detail, dict) else {}

        return {
            # RFID-related extras
            "timers": data.get("timers"),
            "journal": data.get("journal"),

            # Charging station
            "charging_station_stats": data.get("charging_station_stats"),
            "charging_station_detail": cs_detail,

            # Handy derived fields from charging station detail
            "charging_status": cs_status.get("charging_status"),
            "charging_mode": cs_status.get("charging_mode"),

            # Access control / user context
            "permissions": data.get("permissions"),
            "user": data.get("user"),
            "user_installation": data.get("user_installation"),
        }