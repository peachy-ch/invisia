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
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
        str(entry.data[CONF_INSTALLATION_ID]),
        session,
    )

    ids = InvisiaIds(
        rfid_id=str(entry.data[CONF_RFID_ID]),
        user_id=str(entry.data.get(CONF_USER_ID)) if entry.data.get(CONF_USER_ID) else None,
        charging_station_id=str(entry.data.get(CONF_CHARGING_STATION_ID)) if entry.data.get(CONF_CHARGING_STATION_ID) else None,
    )

    coordinator = InvisiaCoordinator(hass, api, ids)
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
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    HA calls *this* when it sees an older config entry version.
    Without this, you get: "Migration handler not found".
    """
    _LOGGER.debug("Migrating Invisia entry %s from version %s", entry.title, entry.version)

    data = dict(entry.data)

    # Normalise numeric fields that may have been stored as strings
    for k in (CONF_INSTALLATION_ID, CONF_RFID_ID, CONF_USER_ID, CONF_CHARGING_STATION_ID):
        if k in data and data[k] not in (None, ""):
            try:
                data[k] = int(data[k])
            except (TypeError, ValueError):
                pass

    # Ensure we have a stable unique_id so re-adds don't create zombies
    installation_id = data.get(CONF_INSTALLATION_ID)
    rfid_id = data.get(CONF_RFID_ID)
    if installation_id and rfid_id and not entry.unique_id:
        unique = f"{installation_id}_{rfid_id}"
        hass.config_entries.async_update_entry(entry, unique_id=unique)

    # Example migration steps if your schema changed:
    # v1 -> v2: allow "disabled" charging mode etc. (no stored fields needed)
    new_version = 2

    hass.config_entries.async_update_entry(entry, data=data, version=new_version)
    _LOGGER.info("Migration of %s successful to version %s", entry.title, new_version)
    return True