from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import InvisiaCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class InvisiaSensorDescription(SensorEntityDescription):
    keypath: str


SENSORS: tuple[InvisiaSensorDescription, ...] = (
    InvisiaSensorDescription(
        key="rfid_profile",
        name="RFID Profile",
        icon="mdi:card-account-details",
        keypath="rfid.profile",
    ),
    InvisiaSensorDescription(
        key="rfid_power",
        name="Charging Power",
        icon="mdi:flash",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=2,
        keypath="stats.current_power_flow",
    ),
    InvisiaSensorDescription(
        key="rfid_energy_charged",
        name="Energy Charged",
        icon="mdi:battery-charging",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        keypath="stats.e_charged",
    ),
    InvisiaSensorDescription(
        key="rfid_status",
        name="Status",
        icon="mdi:ev-station",
        keypath="status.charging_status",
    ),
)


def _get_path(data: dict[str, Any], path: str) -> Any:
    cur: Any = data
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: InvisiaCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([InvisiaSensor(coordinator, entry.entry_id, d) for d in SENSORS])


class InvisiaSensor(CoordinatorEntity[InvisiaCoordinator], SensorEntity):
    entity_description: InvisiaSensorDescription

    def __init__(self, coordinator: InvisiaCoordinator, entry_id: str, description: InvisiaSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_suggested_object_id = f"invisia_{description.key}"
        self._attr_unique_id = f"invisia_{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        val = _get_path(data, self.entity_description.keypath)

        # Power: Invisia already returns kW (your example: 9.46). So don't multiply.
        if self.entity_description.key == "rfid_power":
            try:
                return float(val) if val is not None else 0.0
            except (TypeError, ValueError):
                return 0.0

        # Energy: kWh
        if self.entity_description.key == "rfid_energy_charged":
            try:
                return float(val) if val is not None else 0.0
            except (TypeError, ValueError):
                return 0.0

        # Profile/status: keep it short, because HA will nuke >255 chars.
        if self.entity_description.key == "rfid_profile":
            return (val or "unknown")

        if self.entity_description.key == "rfid_status":
            # Prefer charging station detail status if present
            cs = (data.get("charging_station_detail") or {})
            cs_status = cs.get("status", {}) if isinstance(cs, dict) else {}
            return (cs_status.get("charging_status") or val or "unknown")

        return val

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}

        # Only attach tidy, capped attributes. This is HA, not Splunk.
        if self.entity_description.key != "rfid_status":
            return {}

        attrs: dict[str, Any] = {}

        rfid = data.get("rfid") or {}
        status = data.get("status") or {}
        stats = data.get("stats") or {}

        # Charging station detail often has richer fields
        cs = data.get("charging_station_detail") or {}
        cs_status = cs.get("status", {}) if isinstance(cs, dict) else {}
        cs_stats = cs.get("stats", {}) if isinstance(cs, dict) else {}

        attrs["charging_mode"] = cs_status.get("charging_mode") or status.get("charging_mode") or rfid.get("profile")
        attrs["charging_status"] = cs_status.get("charging_status") or status.get("charging_status")
        attrs["a_max"] = cs_status.get("a_max") or status.get("a_max")
        attrs["ip"] = cs_status.get("ipadresse") or status.get("ipadresse")
        attrs["lock"] = cs_status.get("lock") or status.get("lock")

        # Prefer station stats, then stats endpoint
        attrs["current_power_kw"] = cs_stats.get("current_power_flow") or stats.get("current_power_flow")
        attrs["e_charged_kwh"] = cs_stats.get("e_charged") or stats.get("e_charged")
        attrs["e_sourced_today_kwh"] = cs_stats.get("e_sourced_today") or stats.get("e_sourced_today")

        # Truncate journal and timers hard
        j = data.get("journal") or []
        if isinstance(j, list):
            attrs["journal_recent"] = j[:5]

        t = data.get("timers") or []
        if isinstance(t, list):
            attrs["timers"] = t[:5]

        # Timestamp
        meta = data.get("meta") or {}
        attrs["last_update_utc"] = meta.get("ts")

        # Remove None values to keep it neat
        return {k: v for k, v in attrs.items() if v is not None}