"""Shared stubs and fixtures for Invisia tests.

Patches homeassistant modules into sys.modules BEFORE any integration file
is imported, so the tests run without a full HA install.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Proper inheritable class stubs
# ---------------------------------------------------------------------------

@dataclass(frozen=True, kw_only=True)
class _SensorEntityDescription:
    key: str = ""
    name: str | None = None
    icon: str | None = None
    native_unit_of_measurement: str | None = None
    suggested_display_precision: int | None = None


class _SensorEntity:
    _attr_unique_id: str | None = None
    _attr_suggested_object_id: str | None = None
    _attr_device_info = None
    _attr_has_entity_name: bool = False


class _BinarySensorEntity:
    _attr_has_entity_name: bool = False
    _attr_name: str | None = None
    _attr_unique_id: str | None = None
    _attr_suggested_object_id: str | None = None
    _attr_device_info = None


class _SelectEntity:
    _attr_has_entity_name: bool = False
    _attr_name: str | None = None
    _attr_unique_id: str | None = None
    _attr_suggested_object_id: str | None = None
    _attr_device_info = None
    _attr_options: list[str] = []
    _attr_icon: str | None = None


class _CoordinatorEntity:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, coordinator):
        self.coordinator = coordinator


class _DataUpdateCoordinator:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, hass=None, logger=None, name=None, update_interval=None):
        pass


class _DeviceInfo(dict):
    def __init__(self, **kwargs):
        super().__init__(kwargs)


class _Platform:
    SENSOR = "sensor"
    SELECT = "select"
    BINARY_SENSOR = "binary_sensor"


class _UnitOfPower:
    KILO_WATT = "kW"
    WATT = "W"


class _UnitOfEnergy:
    KILO_WATT_HOUR = "kWh"
    WATT_HOUR = "Wh"


# ---------------------------------------------------------------------------
# Build stub modules and inject before any integration import
# ---------------------------------------------------------------------------

_ha_const = MagicMock()
_ha_const.Platform = _Platform
_ha_const.UnitOfPower = _UnitOfPower
_ha_const.UnitOfEnergy = _UnitOfEnergy

_ha_sensor = MagicMock()
_ha_sensor.SensorEntity = _SensorEntity
_ha_sensor.SensorEntityDescription = _SensorEntityDescription

_ha_binary_sensor = MagicMock()
_ha_binary_sensor.BinarySensorEntity = _BinarySensorEntity

_ha_select = MagicMock()
_ha_select.SelectEntity = _SelectEntity

_ha_update_coord = MagicMock()
_ha_update_coord.DataUpdateCoordinator = _DataUpdateCoordinator
_ha_update_coord.CoordinatorEntity = _CoordinatorEntity
_ha_update_coord.UpdateFailed = RuntimeError

_ha_device_reg = MagicMock()
_ha_device_reg.DeviceInfo = _DeviceInfo

_ha_entity = MagicMock()
_ha_entity.DeviceInfo = _DeviceInfo

_HA_STUBS: dict[str, object] = {
    "homeassistant": MagicMock(),
    "homeassistant.core": MagicMock(),
    "homeassistant.const": _ha_const,
    "homeassistant.config_entries": MagicMock(),
    "homeassistant.data_entry_flow": MagicMock(),
    "homeassistant.helpers": MagicMock(),
    "homeassistant.helpers.update_coordinator": _ha_update_coord,
    "homeassistant.helpers.entity": _ha_entity,
    "homeassistant.helpers.entity_platform": MagicMock(),
    "homeassistant.helpers.device_registry": _ha_device_reg,
    "homeassistant.helpers.aiohttp_client": MagicMock(),
    "homeassistant.components": MagicMock(),
    "homeassistant.components.sensor": _ha_sensor,
    "homeassistant.components.binary_sensor": _ha_binary_sensor,
    "homeassistant.components.select": _ha_select,
}

for _mod, _stub in _HA_STUBS.items():
    sys.modules.setdefault(_mod, _stub)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_response(
    status: int = 200,
    json_data=None,
    text_data: str | None = None,
    raise_content_type: bool = False,
):
    """Return a mock aiohttp ClientResponse."""
    import aiohttp

    resp = MagicMock()
    resp.status = status
    resp.headers = {}

    if raise_content_type:
        req_info = MagicMock()
        err = aiohttp.ContentTypeError(req_info, ())
        resp.json = AsyncMock(side_effect=err)
    else:
        resp.json = AsyncMock(return_value=json_data)

    resp.text = AsyncMock(return_value=text_data or "")
    return resp


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def api(mock_session):
    from custom_components.invisia.api import InvisiaAPI

    inst = InvisiaAPI(
        email="test@example.com",
        password="secret",
        installation_id="42",
        session=mock_session,
    )
    inst._access_token = "tok_access"
    inst._refresh_token = "tok_refresh"
    return inst
