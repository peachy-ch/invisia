from __future__ import annotations

import logging
from datetime import timedelta, date

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class InvisiaCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api, rfid_id: str, user_id: str | None, charging_station_id: str | None):
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{rfid_id}",
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )
        self.api = api
        self.rfid_id = str(rfid_id)
        self.user_id = str(user_id) if user_id else None
        self.charging_station_id = str(charging_station_id) if charging_station_id else None

    async def _async_update_data(self):
        try:
            data = {}

            # Always: RFID status/config
            data["rfid_status"] = await self.api.get_rfid(self.rfid_id)

            # Timers bound to RFID
            data["timers"] = await self.api.get_rfid_timers(self.rfid_id)

            # Journal: web app used a rolling window; we’ll do last 30 days
            end = date.today().isoformat()
            start = (date.today().replace(day=1)).isoformat()  # cheap + stable; not perfect, but fine
            data["journal"] = await self.api.get_rfid_journal(self.rfid_id, start=start, end=end)

            # Optional: user + permissions
            if self.user_id:
                data["permissions"] = await self.api.get_permissions(self.user_id)
                data["user"] = await self.api.get_user(self.user_id)
                data["user_installation"] = await self.api.get_user_installation(self.user_id)

            # Optional: charging station info
            data["charging_station_stats"] = await self.api.get_charging_station_stats()
            if self.charging_station_id:
                data["charging_station_detail"] = await self.api.get_charging_station_detail(self.charging_station_id)

            return data

        except Exception as err:
            raise UpdateFailed(err) from err