from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_INSTALLATION_ID,
    CONF_RFID_ID,
    CONF_USER_ID,
    CONF_CHARGING_STATION_ID,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_INSTALLATION_ID): vol.Coerce(int),
        vol.Required(CONF_RFID_ID): vol.Coerce(int),
        vol.Optional(CONF_CHARGING_STATION_ID): vol.Coerce(int),
        vol.Optional(CONF_USER_ID): vol.Coerce(int),
    }
)


class InvisiaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input=None) -> FlowResult:
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA)

        unique = f"{user_input[CONF_INSTALLATION_ID]}_{user_input[CONF_RFID_ID]}"
        await self.async_set_unique_id(unique)
        self._abort_if_unique_id_configured()

        title = f"Invisia RFID {user_input[CONF_RFID_ID]}"
        return self.async_create_entry(title=title, data=user_input)