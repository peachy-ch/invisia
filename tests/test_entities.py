"""Entity-level tests against a real app.invisia.ch payload.

Covers the RFID-only installation shape (has_charging_stations=false), where the
charging-station endpoints carry nothing and the RFID block from get_rfid() is
the only live source. An exception raised from native_value or
extra_state_attributes aborts async_write_ha_state, so HA silently leaves the
entity frozen on its last value — these tests assert on values, not just on
"does not raise".
"""
from __future__ import annotations

import pytest

from custom_components.invisia.binary_sensor import InvisiaCarPluggedIn
from custom_components.invisia.select import InvisiaChargingModeSelect
from custom_components.invisia.sensor import SENSORS, InvisiaSensor, _sub_dict


# Captured from GET /api/cockpit/installations/272/rfids/2476 while charging.
# The physical tag serial and the wallbox LAN IP are genericized; everything else
# is verbatim, so the tests still exercise the real payload shape and values.
LIVE_PAYLOAD = {
    "rfid": {
        "id": 2476,
        "rfid_tag": "0A1B2C3D",
        "description": "",
        "profile": "instant",
        "name": "Tom Peach",
    },
    "stats": {
        "current_power_flow": 11.09,
        "e_sourced_today": 0.0,
        "charging_time_minutes": 15,
        "e_charged": 1.764,
        "start_time": "2026-09-15T17:26:06Z",
    },
    "alert": None,
    "status": {
        "time": "2026-09-15T17:39:01Z",
        "soc": 0,
        "charging_status": "charging",
        "rfid_mode": True,
        "charging_mode": "instant",
        "a_max": 32,
        "ladekabel": 32,
        "zoe_modus": 0,
        "ipadresse": "192.0.2.221",
        "lock": 0,
    },
    "timers": [],
    "journal": [{"entry_type": "rfid_charging_session", "id": 11210197}],
    "stats_history": [{"time": "2026-08-16T00:00:00", "flow": None}],
    # RFID-only install: the detail endpoint 404s, so the coordinator stores {}.
    "charging_station_detail": {},
}

# What api.py used to hand back for a non-JSON 404. "status" holds the HTTP code,
# which shadows the status object every entity reads from.
NON_JSON_SENTINEL = {"_non_json": True, "status": 404, "text": ""}


class FakeCoordinator:
    """Entities only touch .data and the id properties."""

    def __init__(self, data):
        self.data = data
        self.last_update_success = True

    @property
    def installation_id(self):
        return "272"

    @property
    def rfid_id(self):
        return "2476"

    @property
    def charging_station_id(self):
        return "21401417"


def sensor_for(key: str, data) -> InvisiaSensor:
    for desc in SENSORS:
        if desc.key == key:
            return InvisiaSensor(FakeCoordinator(data), "entry", desc)
    raise KeyError(key)


def plugged_in(data) -> InvisiaCarPluggedIn:
    return InvisiaCarPluggedIn(FakeCoordinator(data), "272", "21401417")


def charging_mode(data) -> InvisiaChargingModeSelect:
    return InvisiaChargingModeSelect(FakeCoordinator(data), "entry")


# ---------------------------------------------------------------------------
# _sub_dict
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "data,path,expected",
    [
        ({"a": {"b": 1}}, ("a",), {"b": 1}),
        ({"a": {"b": {"c": 1}}}, ("a", "b"), {"c": 1}),
        ({"a": {"b": 1}}, ("a", "b"), {}),
        ({"a": 404}, ("a", "b"), {}),
        ({"a": None}, ("a",), {}),
        ({}, ("a",), {}),
        (None, ("a",), {}),
        (["not", "a", "dict"], ("a",), {}),
    ],
)
def test_sub_dict(data, path, expected):
    assert _sub_dict(data, *path) == expected


# ---------------------------------------------------------------------------
# Live values must actually reach the state machine
# ---------------------------------------------------------------------------

def test_live_power_is_reported():
    assert sensor_for("rfid_power", LIVE_PAYLOAD).native_value == 11.09


def test_live_energy_is_reported():
    assert sensor_for("rfid_energy_charged", LIVE_PAYLOAD).native_value == 1.764


def test_live_status_is_reported():
    assert sensor_for("rfid_status", LIVE_PAYLOAD).native_value == "charging"


def test_live_profile_is_reported():
    assert sensor_for("rfid_profile", LIVE_PAYLOAD).native_value == "instant"


def test_time_series_does_not_clobber_live_stats():
    """Regression for e8d040d: stats_history must not displace the stats dict.

    get_rfid_stats() returns 30 daily buckets. When that landed in data["stats"],
    _get_path() could not traverse the list and both sensors pinned to 0.0 while
    the car was visibly charging.
    """
    assert isinstance(LIVE_PAYLOAD["stats"], dict)
    assert isinstance(LIVE_PAYLOAD["stats_history"], list)
    assert sensor_for("rfid_power", LIVE_PAYLOAD).native_value == 11.09
    assert sensor_for("rfid_energy_charged", LIVE_PAYLOAD).native_value == 1.764


def test_status_attributes_populated_on_rfid_only_install():
    attrs = sensor_for("rfid_status", LIVE_PAYLOAD).extra_state_attributes

    assert attrs["charging_mode"] == "instant"
    assert attrs["charging_status"] == "charging"
    assert attrs["a_max"] == 32
    assert attrs["ip"] == "192.0.2.221"
    assert attrs["current_power_kw"] == 11.09
    assert attrs["e_charged_kwh"] == 1.764
    assert attrs["journal_recent"] == [{"entry_type": "rfid_charging_session", "id": 11210197}]


def test_last_update_utc_comes_from_the_status_block():
    """There is no "meta" block in the payload, so this attribute was always dropped."""
    attrs = sensor_for("rfid_status", LIVE_PAYLOAD).extra_state_attributes

    assert attrs["last_update_utc"] == "2026-09-15T17:39:01Z"


def test_binary_sensor_on_while_charging():
    assert plugged_in(LIVE_PAYLOAD).is_on is True


def test_binary_sensor_on_when_plugged_but_not_charging():
    data = {**LIVE_PAYLOAD, "status": {**LIVE_PAYLOAD["status"], "charging_status": "carPluggedIn"}}

    assert plugged_in(data).is_on is True


def test_binary_sensor_attributes_fall_back_to_rfid_status():
    """The detail block is empty on RFID-only installs; the attributes must not be."""
    attrs = plugged_in(LIVE_PAYLOAD).extra_state_attributes

    assert attrs["charging_status"] == "charging"
    assert attrs["charging_mode"] == "instant"
    assert attrs["a_max"] == 32
    assert attrs["ladekabel"] == 32
    assert attrs["ip"] == "192.0.2.221"
    assert attrs["soc"] == 0


def test_select_reflects_rfid_profile():
    assert charging_mode(LIVE_PAYLOAD).current_option == "instant"


def test_select_falls_back_to_status_block():
    assert charging_mode({**LIVE_PAYLOAD, "rfid": {}}).current_option == "instant"


def test_charging_station_detail_wins_when_present():
    """Installations that do have a station keep preferring its richer payload."""
    data = {
        **LIVE_PAYLOAD,
        "charging_station_detail": {
            "status": {"charging_status": "carPluggedIn", "charging_mode": "optimized", "a_max": 16},
            "stats": {"current_power_flow": 3.7, "e_charged": 0.5},
        },
    }

    assert sensor_for("rfid_status", data).native_value == "carPluggedIn"
    attrs = sensor_for("rfid_status", data).extra_state_attributes
    assert attrs["charging_mode"] == "optimized"
    assert attrs["a_max"] == 16
    # Power/energy still come from the RFID stats block; the station is a fallback.
    assert sensor_for("rfid_power", data).native_value == 11.09


def test_select_tracks_the_rfid_profile_not_the_station():
    """The select writes set_rfid_profile, so it must read rfid.profile back.

    Reporting the station's charging_mode here would make the control show a value
    it cannot actually set.
    """
    data = {
        **LIVE_PAYLOAD,
        "charging_station_detail": {"status": {"charging_mode": "optimized"}},
    }

    assert charging_mode(data).current_option == "instant"


def test_power_falls_back_to_station_when_rfid_stats_missing():
    data = {
        "status": {"charging_status": "charging"},
        "charging_station_detail": {"stats": {"current_power_flow": 7.4, "e_charged": 2.5}},
    }

    assert sensor_for("rfid_power", data).native_value == 7.4
    assert sensor_for("rfid_energy_charged", data).native_value == 2.5


# ---------------------------------------------------------------------------
# Unknown must not be reported as a confident "off"
# ---------------------------------------------------------------------------

def test_binary_sensor_unknown_when_nothing_reported():
    assert plugged_in({}).is_on is None
    assert plugged_in(None).is_on is None


def test_binary_sensor_off_when_idle():
    data = {**LIVE_PAYLOAD, "status": {**LIVE_PAYLOAD["status"], "charging_status": "disabled"}}

    assert plugged_in(data).is_on is False


# ---------------------------------------------------------------------------
# REGRESSION: the payload that froze every entity in production
# ---------------------------------------------------------------------------

def test_charging_station_sentinel_no_longer_freezes_entities():
    """The exact production failure: charging_station_detail held the 404 sentinel.

    Its "status" key held the int 404, so detail["status"].get("charging_status")
    raised AttributeError inside async_write_ha_state. HA logged "Unexpected error
    updating listener" every 30s and left the entities on their last value.

    Everything else in the payload was healthy, so once the raise is gone the
    RFID blocks must carry the live values again.
    """
    data = {**LIVE_PAYLOAD, "charging_station_detail": NON_JSON_SENTINEL}

    assert sensor_for("rfid_status", data).native_value == "charging"
    assert sensor_for("rfid_power", data).native_value == 11.09
    assert sensor_for("rfid_energy_charged", data).native_value == 1.764
    assert plugged_in(data).is_on is True
    assert charging_mode(data).current_option == "instant"

    attrs = sensor_for("rfid_status", data).extra_state_attributes
    assert attrs["charging_status"] == "charging"
    assert attrs["last_update_utc"] == "2026-09-15T17:39:01Z"
    assert plugged_in(data).extra_state_attributes["ip"] == "192.0.2.221"


def test_every_block_poisoned_degrades_to_unknown():
    """Worst case: no block has the expected type. Unknown, never a raise."""
    poisoned = {
        "rfid": 404,
        "stats": 404,
        "status": 404,
        "timers": 404,
        "journal": NON_JSON_SENTINEL,
        "charging_station_detail": NON_JSON_SENTINEL,
    }

    assert sensor_for("rfid_status", poisoned).native_value == "unknown"
    assert sensor_for("rfid_profile", poisoned).native_value == "unknown"
    assert sensor_for("rfid_power", poisoned).native_value == 0.0
    assert sensor_for("rfid_energy_charged", poisoned).native_value == 0.0
    assert sensor_for("rfid_status", poisoned).extra_state_attributes == {}
    assert plugged_in(poisoned).is_on is None
    assert charging_mode(poisoned).current_option is None


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(None, id="no_data_at_all"),
        pytest.param({}, id="empty"),
        pytest.param({**LIVE_PAYLOAD, "status": None}, id="status_none"),
        pytest.param({**LIVE_PAYLOAD, "stats": None}, id="stats_none"),
        pytest.param({**LIVE_PAYLOAD, "rfid": None}, id="rfid_none"),
        pytest.param({**LIVE_PAYLOAD, "status": "oops"}, id="status_str"),
        pytest.param({**LIVE_PAYLOAD, "stats": 404}, id="stats_int"),
        pytest.param({**LIVE_PAYLOAD, "journal": None}, id="journal_none"),
        pytest.param({**LIVE_PAYLOAD, "timers": {}}, id="timers_dict"),
        pytest.param({**LIVE_PAYLOAD, "charging_station_detail": NON_JSON_SENTINEL}, id="cs_sentinel"),
        pytest.param({**LIVE_PAYLOAD, "charging_station_detail": None}, id="cs_none"),
        pytest.param({**LIVE_PAYLOAD, "charging_station_detail": ["x"]}, id="cs_list"),
        pytest.param({**LIVE_PAYLOAD, "status": {"charging_status": None}}, id="charging_status_none"),
    ],
)
def test_entities_never_raise_on_degraded_payloads(data):
    """Any raise here freezes the entity forever, so every path must degrade."""
    for key in ("rfid_power", "rfid_energy_charged", "rfid_profile", "rfid_status"):
        _ = sensor_for(key, data).native_value

    _ = sensor_for("rfid_status", data).extra_state_attributes
    _ = plugged_in(data).is_on
    _ = plugged_in(data).extra_state_attributes
    _ = charging_mode(data).current_option
