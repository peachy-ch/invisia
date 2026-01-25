from __future__ import annotations

import async_timeout
import logging
from typing import Any

from aiohttp import ClientResponseError, ContentTypeError

from .const import BASE_URL

_LOGGER = logging.getLogger(__name__)


class InvisiaAPI:
    """Tiny wrapper around the (unofficial) Invisia web backend."""

    def __init__(self, email: str, password: str, installation_id: str, session):
        self._email = email
        self._password = password
        self._installation_id = str(installation_id)
        self._session = session

        self._access_token: str | None = None
        self._refresh_token: str | None = None

    async def login(self) -> None:
        url = f"{BASE_URL}/api/authentication/token/"
        payload = {"email": self._email, "password": self._password}

        async with async_timeout.timeout(20):
            resp = await self._session.post(
                url,
                json=payload,
                headers={"X-Installation-Id": self._installation_id},
            )
            # If this isn't JSON, it'll explode here and that's fine: creds / backend busted.
            data = await resp.json()

        self._access_token = data.get("access")
        self._refresh_token = data.get("refresh")

        if not self._access_token:
            raise RuntimeError("Invisia login failed (no access token)")

        if not self._refresh_token:
            # Some backends may not return refresh, but most do.
            _LOGGER.debug("Invisia login returned no refresh token")

    async def refresh(self) -> None:
        """Refresh access token. Requires refresh token in request body."""
        if not self._refresh_token:
            # Fall back to full login.
            await self.login()
            return

        url = f"{BASE_URL}/api/authentication/token/refresh/"
        payload = {"refresh": self._refresh_token}

        async with async_timeout.timeout(20):
            resp = await self._session.post(
                url,
                json=payload,
                headers={"X-Installation-Id": self._installation_id},
            )
            data = await resp.json()

        self._access_token = data.get("access") or self._access_token
        # Some refresh responses may also rotate refresh token.
        self._refresh_token = data.get("refresh") or self._refresh_token

        if not self._access_token:
            raise RuntimeError("Invisia token refresh failed (no access token)")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        allow_non_json: bool = False,
    ):
        """Perform an authenticated request. Optionally tolerate HTML/text bodies."""
        if not self._access_token:
            await self.login()

        url = f"{BASE_URL}{path}"
        headers = {
            "Accept": "application/json",
            "X-Authorization": f"Bearer {self._access_token}",
            "X-Installation-Id": self._installation_id,
        }

        async with async_timeout.timeout(20):
            resp = await self._session.request(
                method, url, headers=headers, params=params, json=json_body
            )

            try:
                data = await resp.json()
            except ContentTypeError:
                # Invisia sometimes returns HTML error pages (yes, really).
                text = await resp.text()
                if allow_non_json:
                    return {"_non_json": True, "status": resp.status, "text": text[:500]}
                raise RuntimeError(
                    f"Invisia API returned non-JSON for {method} {path}: {resp.status} {text[:200]}"
                )

        # Token invalid -> refresh/login and retry once
        if isinstance(data, dict) and data.get("code") == "token_not_valid":
            await self.refresh()
            return await self._request(
                method,
                path,
                params=params,
                json_body=json_body,
                allow_non_json=allow_non_json,
            )

        # Raise for non-2xx if we actually got JSON back with errors
        if resp.status >= 400 and isinstance(data, dict):
            # Keep it readable in logs.
            raise RuntimeError(f"Invisia API error {resp.status} for {method} {path}: {data}")

        return data

    # ---- RFID ----
    async def get_rfid(self, rfid_id: str):
        return await self._request(
            "GET",
            f"/api/cockpit/installations/{self._installation_id}/rfids/{rfid_id}",
        )

    async def set_rfid_profile(self, rfid_id: str, profile: str):
        # profile: "instant" | "optimized" | "disabled"
        return await self._request(
            "PATCH",
            f"/api/cockpit/installations/{self._installation_id}/rfids/{rfid_id}",
            json_body={"id": int(rfid_id), "profile": profile},
        )

    async def get_rfid_journal(self, rfid_id: str, start: str, end: str):
        return await self._request(
            "GET",
            f"/api/cockpit/installations/{self._installation_id}/rfids/{rfid_id}/journal",
            params={"start": start, "end": end},
            # Journal can occasionally misbehave; don't brick the whole integration.
            allow_non_json=True,
        )

    async def get_rfid_timers(self, rfid_id: str):
        return await self._request(
            "GET",
            f"/api/cockpit/installations/{self._installation_id}/timers/",
            params={"object_id": rfid_id, "object_type": "rfid"},
            allow_non_json=True,
        )

    async def get_rfid_stats(self, rfid_id: str, start: str, end: str, granularity: str):
        # This endpoint is the flakiest. Treat it as optional upstream.
        return await self._request(
            "GET",
            f"/api/statistics/{self._installation_id}/rfid/{rfid_id}",
            params={"start": start, "end": end, "granularity": granularity},
            allow_non_json=True,
        )

    async def get_rfid_stats_zev(self, rfid_id: str, start: str, end: str, granularity: str):
        return await self._request(
            "GET",
            f"/api/statistics/{self._installation_id}/rfid/{rfid_id}/zev",
            params={"start": start, "end": end, "granularity": granularity},
            allow_non_json=True,
        )

    # ---- Charging Stations ----
    async def get_charging_station_stats(self):
        return await self._request(
            "GET",
            f"/api/cockpit/installations/{self._installation_id}/objects/charging_stations/stats",
            allow_non_json=True,
        )

    async def get_charging_station_detail(self, charging_station_id: str):
        return await self._request(
            "GET",
            f"/api/cockpit/installations/{self._installation_id}/charging_stations/{charging_station_id}",
            allow_non_json=True,
        )

    # The following endpoints are NOT reliable across accounts/roles.
    # Leave them out unless you have confirmed they work.