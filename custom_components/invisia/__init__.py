from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import InvisiaAPI
from .coordinator import InvisiaCoordinator, InvisiaIds
from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_INSTALLATION_ID,
    CONF_RFID_ID,
    CONF_USER_ID,
    CONF_CHARGING_STATION_ID,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)

    api = InvisiaAPI(
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        installation_id=int(entry.data[CONF_INSTALLATION_ID]),
        session=session,
    )

    ids = InvisiaIds(
        installation_id=int(entry.data[CONF_INSTALLATION_ID]),
        rfid_id=int(entry.data[CONF_RFID_ID]),
        user_id=int(entry.data[CONF_USER_ID]) if entry.data.get(CONF_USER_ID) else None,
        charging_station_id=int(entry.data[CONF_CHARGING_STATION_ID]) if entry.data.get(CONF_CHARGING_STATION_ID) else None,
    )

    coordinator = InvisiaCoordinator(hass=hass, api=api, ids=ids)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "entry": entry,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok