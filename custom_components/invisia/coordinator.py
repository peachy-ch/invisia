from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import InvisiaAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=30)


@dataclass(frozen=True)
class InvisiaIds:
    installation_id: int
    rfid_id: int
    user_id: int | None = None
    charging_station_id: int | None = None


class InvisiaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Central data coordinator for Invisia."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: InvisiaAPI,
        ids: InvisiaIds,
    ) -> None:
        self.hass = hass
        self.api = api
        self.ids = ids

        super().__init__(
            hass,
            _LOGGER,
            name=f"Invisia RFID {ids.rfid_id}",
            update_interval=UPDATE_INTERVAL,
        )

    # ---------------------------------------------------------------------
    # Backwards-compat properties (DO NOT REMOVE)
    # ---------------------------------------------------------------------

    @property
    def installation_id(self) -> str:
        return str(self.ids.installation_id)

    @property
    def rfid_id(self) -> str:
        return str(self.ids.rfid_id)

    @property
    def user_id(self) -> str | None:
        if self.ids.user_id is None:
            return None
        return str(self.ids.user_id)

    @property
    def charging_station_id(self) -> str | None:
        if self.ids.charging_station_id is None:
            return None
        return str(self.ids.charging_station_id)

    # ---------------------------------------------------------------------
    # Device info helpers (used by entities)
    # ---------------------------------------------------------------------

    @property
    def rfid_device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, f"rfid_{self.installation_id}_{self.rfid_id}")},
            "name": f"Invisia RFID {self.rfid_id}",
            "manufacturer": "Invisia",
            "model": "RFID",
        }

    @property
    def charging_station_device_info(self) -> dict[str, Any] | None:
        if self.charging_station_id is None:
            return None

        return {
            "identifiers": {
                (DOMAIN, f"charging_station_{self.installation_id}_{self.charging_station_id}")
            },
            "name": f"Invisia Charging Station {self.charging_station_id}",
            "manufacturer": "Invisia",
            "model": "Charging Station",
        }

    # ---------------------------------------------------------------------
    # Data refresh
    # ---------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {}

        # --- Core RFID state (THIS MUST WORK) ---
        try:
            data.update(await self.api.get_rfid(self.ids.rfid_id))
        except Exception as err:
            _LOGGER.error("Invisia get_rfid failed", exc_info=err)
            raise

        # --- Journal (best-effort) ---
        try:
            data["journal"] = await self.api.get_rfid_journal(self.ids.rfid_id)
        except Exception as err:
            _LOGGER.warning("Invisia get_journal failed (ignored)", exc_info=err)

        # --- Stats (broken server-side sometimes; ignore failures) ---
        try:
            data["stats"] = await self.api.get_rfid_stats(self.ids.rfid_id)
        except Exception as err:
            _LOGGER.warning("Invisia stats fetch failed (ignored)", exc_info=err)

        return data
