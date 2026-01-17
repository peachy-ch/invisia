import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import InvisiaAPI
from .const import (
    DOMAIN,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_INSTALLATION_ID,
    CONF_RFID_ID,
    CONF_USER_ID,
    CONF_CHARGING_STATION_ID,
)


class InvisiaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = InvisiaAPI(
                user_input[CONF_EMAIL],
                user_input[CONF_PASSWORD],
                user_input[CONF_INSTALLATION_ID],
                session,
            )

            try:
                await api.login()
                return self.async_create_entry(title="Invisia", data=user_input)
            except Exception:
                errors["base"] = "auth_failed"

        schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_INSTALLATION_ID): str,
                vol.Required(CONF_RFID_ID): str,
                # Optional but useful for “full web app” coverage:
                vol.Optional(CONF_USER_ID): str,
                vol.Optional(CONF_CHARGING_STATION_ID): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)