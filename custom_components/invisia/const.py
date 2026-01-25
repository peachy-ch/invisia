"""Constants for the Invisia integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "invisia"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_INSTALLATION_ID = "installation_id"
CONF_RFID_ID = "rfid_id"
CONF_USER_ID = "user_id"
CONF_CHARGING_STATION_ID = "charging_station_id"

BASE_URL = "https://app.invisia.ch"

# Poll interval (seconds). Coordinator uses its own scheduling; keep as simple int for now.
SCAN_INTERVAL = 30

# Home Assistant platforms this integration provides.
PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SELECT,
    Platform.BINARY_SENSOR,

]
