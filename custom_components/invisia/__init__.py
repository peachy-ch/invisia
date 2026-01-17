from __future__ import annotations

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import InvisiaAPI
from .coordinator import InvisiaCoordinator
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


async def async_setup_entry(hass, entry):
    session = async_get_clientsession(hass)
    api = InvisiaAPI(
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_INSTALLATION_ID],
        session,
    )

    coordinator = InvisiaCoordinator(
        hass,
        api,
        entry.data[CONF_RFID_ID],
        entry.data.get(CONF_USER_ID),
        entry.data.get(CONF_CHARGING_STATION_ID),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "entry": entry,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok