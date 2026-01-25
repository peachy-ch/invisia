from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
import time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .api import InvisiaAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class InvisiaIds:
    rfid_id: str
    user_id: str | None = None
    charging_station_id: str | None = None


class InvisiaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, api: InvisiaAPI, ids: InvisiaIds) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} RFID {ids.rfid_id}",
            update_interval=timedelta(seconds=30),
        )
        self.api = api
        self.ids = ids

    async def _async_update_data(self) -> dict[str, Any]:
        t0 = time.perf_counter()

        # Always return a dict, even on partial failure (HA hates None)
        data: dict[str, Any] = {
            "rfid": None,
            "status": None,
            "stats": {},
            "timers": [],
            "journal": [],
            "charging_station_detail": None,
            "charging_station_stats": None,
            "meta": {"ts": dt_util.utcnow().isoformat()},
        }

        try:
            # This is the only call you *actually* need to keep the integration useful.
            rfid_payload = await self.api.get_rfid(self.ids.rfid_id)

            # The API returns a big dict that contains rfid/status/stats/etc.
            if isinstance(rfid_payload, dict):
                data["rfid"] = rfid_payload.get("rfid")
                data["status"] = rfid_payload.get("status")
                # Sometimes stats are already embedded here, sometimes not
                data["stats"] = rfid_payload.get("stats") or {}
            else:
                data["rfid"] = rfid_payload

            # Optional: station detail/stats
            if self.ids.charging_station_id:
                try:
                    cs_detail = await self.api.get_charging_station_detail(self.ids.charging_station_id)
                    if isinstance(cs_detail, dict) and cs_detail.get("_non_json"):
                        _LOGGER.debug("Charging station detail returned non-JSON (status=%s)", cs_detail.get("status"))
                    else:
                        data["charging_station_detail"] = cs_detail
                except Exception:
                    _LOGGER.debug("Charging station detail fetch failed", exc_info=True)

            try:
                cs_stats = await self.api.get_charging_station_stats()
                if isinstance(cs_stats, dict) and cs_stats.get("_non_json"):
                    _LOGGER.debug("Charging station stats returned non-JSON (status=%s)", cs_stats.get("status"))
                else:
                    data["charging_station_stats"] = cs_stats
            except Exception:
                _LOGGER.debug("Charging station stats fetch failed", exc_info=True)

            # Optional: timers and journal (hard-capped)
            try:
                timers = await self.api.get_rfid_timers(self.ids.rfid_id)
                if isinstance(timers, dict) and timers.get("_non_json"):
                    _LOGGER.debug("Timers returned non-JSON (status=%s)", timers.get("status"))
                elif isinstance(timers, list):
                    data["timers"] = timers[:5]
            except Exception:
                _LOGGER.debug("Timers fetch failed", exc_info=True)

            try:
                start = (dt_util.utcnow() - timedelta(days=7)).isoformat()
                end = dt_util.utcnow().isoformat()
                journal = await self.api.get_rfid_journal(self.ids.rfid_id, start=start, end=end)
                if isinstance(journal, dict) and journal.get("_non_json"):
                    _LOGGER.debug("Journal returned non-JSON (status=%s)", journal.get("status"))
                elif isinstance(journal, list):
                    data["journal"] = journal[:10]
            except Exception:
                _LOGGER.debug("Journal fetch failed", exc_info=True)

            # Optional: stats endpoint (known to HTML-500). Never fatal.
            try:
                start = (dt_util.utcnow() - timedelta(hours=24)).isoformat()
                end = dt_util.utcnow().isoformat()
                stats = await self.api.get_rfid_stats(self.ids.rfid_id, start=start, end=end, granularity="total")
                if isinstance(stats, dict) and stats.get("_non_json"):
                    _LOGGER.warning(
                        "Invisia stats returned non-JSON (status=%s). Ignoring.",
                        stats.get("status"),
                    )
                elif isinstance(stats, dict):
                    # API can return {"stats": {...}} or just {...}
                    data["stats"] = stats.get("stats") if "stats" in stats else stats
            except Exception:
                _LOGGER.warning("Invisia stats fetch failed (ignored)", exc_info=True)

        except Exception:
            # Keep last partial data so entities don't go unavailable every refresh
            _LOGGER.exception("Unexpected error fetching invisia RFID %s data", self.ids.rfid_id)

        dt = time.perf_counter() - t0
        _LOGGER.debug(
            "Finished fetching invisia RFID %s data in %.3f seconds (rfid_present=%s)",
            self.ids.rfid_id,
            dt,
            bool(data.get("rfid")),
        )
        return data