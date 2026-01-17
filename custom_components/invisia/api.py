from __future__ import annotations

import async_timeout

from .const import BASE_URL


class InvisiaAPI:
    def __init__(self, email: str, password: str, installation_id: str, session):
        self._email = email
        self._password = password
        self._installation_id = str(installation_id)
        self._session = session
        self._access_token: str | None = None

    async def login(self) -> None:
        url = f"{BASE_URL}/api/authentication/token/"
        payload = {"email": self._email, "password": self._password}

        async with async_timeout.timeout(15):
            resp = await self._session.post(
                url,
                json=payload,
                headers={"X-Installation-Id": self._installation_id},
            )
            data = await resp.json()

        self._access_token = data.get("access")
        if not self._access_token:
            raise RuntimeError("Invisia login failed")

    async def refresh(self) -> None:
        url = f"{BASE_URL}/api/authentication/token/refresh/"

        async with async_timeout.timeout(15):
            resp = await self._session.post(
                url,
                headers={"X-Installation-Id": self._installation_id},
            )
            data = await resp.json()

        self._access_token = data.get("access")
        if not self._access_token:
            raise RuntimeError("Invisia token refresh failed")

    async def _request(self, method: str, path: str, *, params=None, json_body=None):
        if not self._access_token:
            await self.login()

        url = f"{BASE_URL}{path}"
        headers = {
            "Accept": "application/json",
            "X-Authorization": f"Bearer {self._access_token}",
            "X-Installation-Id": self._installation_id,
        }

        async with async_timeout.timeout(15):
            resp = await self._session.request(
                method, url, headers=headers, params=params, json=json_body
            )
            data = await resp.json()

        if isinstance(data, dict) and data.get("code") == "token_not_valid":
            await self.refresh()
            return await self._request(method, path, params=params, json_body=json_body)

        return data

    # ---- RFID ----
    async def get_rfid(self, rfid_id: str):
        return await self._request(
            "GET",
            f"/api/cockpit/installations/{self._installation_id}/rfids/{rfid_id}",
        )

    async def set_rfid_profile(self, rfid_id: str, profile: str):
        # profile: "instant" | "optimized"
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
        )

    async def get_rfid_timers(self, rfid_id: str):
        return await self._request(
            "GET",
            f"/api/cockpit/installations/{self._installation_id}/timers/",
            params={"object_id": rfid_id, "object_type": "rfid"},
        )

    async def get_rfid_stats(self, rfid_id: str, start: str, end: str, granularity: str):
        return await self._request(
            "GET",
            f"/api/statistics/{self._installation_id}/rfid/{rfid_id}",
            params={"start": start, "end": end, "granularity": granularity},
        )

    async def get_rfid_stats_zev(self, rfid_id: str, start: str, end: str, granularity: str):
        return await self._request(
            "GET",
            f"/api/statistics/{self._installation_id}/rfid/{rfid_id}/zev",
            params={"start": start, "end": end, "granularity": granularity},
        )

    # ---- Charging Stations ----
    async def get_charging_station_stats(self):
        return await self._request(
            "GET",
            f"/api/cockpit/installations/{self._installation_id}/objects/charging_stations/stats",
        )

    async def get_charging_station_detail(self, charging_station_id: str):
        return await self._request(
            "GET",
            f"/api/cockpit/installations/{self._installation_id}/charging_stations/{charging_station_id}",
        )

    async def get_charging_station_timeseries(self, start: str, end: str, granularity: str):
        return await self._request(
            "GET",
            f"/api/statistics/{self._installation_id}/object/charging_stations",
            params={"start": start, "end": end, "granularity": granularity},
        )

    async def get_charging_station_timeseries_zev(self, start: str, end: str, granularity: str):
        return await self._request(
            "GET",
            f"/api/statistics/{self._installation_id}/object/charging_stations/zev",
            params={"start": start, "end": end, "granularity": granularity},
        )

    # ---- Permissions / User ----
    async def get_permissions(self, user_id: str):
        return await self._request(
            "GET",
            f"/api/cockpit/installations/{self._installation_id}/objects/permissions",
            params={"user_id": user_id},
        )

    async def get_user(self, user_id: str):
        return await self._request("GET", f"/api/users/{user_id}/")

    async def get_user_installation(self, user_id: str):
        return await self._request(
            "GET",
            f"/api/cockpit/users/{user_id}/installations/{self._installation_id}",
        )