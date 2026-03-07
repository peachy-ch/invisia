"""Unit tests for coordinator._async_update_data."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.invisia.coordinator import InvisiaCoordinator, InvisiaIds


def _make_coordinator(api, ids: InvisiaIds) -> InvisiaCoordinator:
    """Create an InvisiaCoordinator without going through __init__."""
    inst = object.__new__(InvisiaCoordinator)
    inst.api = api
    inst.ids = ids
    return inst


@pytest.fixture
def ids_no_cs():
    return InvisiaIds(installation_id=42, rfid_id=7)


@pytest.fixture
def ids_with_cs():
    return InvisiaIds(installation_id=42, rfid_id=7, charging_station_id=99)


# ---------------------------------------------------------------------------
# Basic success paths
# ---------------------------------------------------------------------------

async def test_update_success_populates_all_keys(ids_no_cs):
    api = MagicMock()
    api.get_rfid = AsyncMock(return_value={"rfid": {"profile": "instant"}, "status": {}})
    api.get_rfid_journal = AsyncMock(return_value=[{"id": 1}])
    api.get_rfid_stats = AsyncMock(return_value={"current_power_flow": 5.0})

    result = await _make_coordinator(api, ids_no_cs)._async_update_data()

    assert result["rfid"]["profile"] == "instant"
    assert result["journal"] == [{"id": 1}]
    assert result["stats"]["current_power_flow"] == 5.0
    assert "charging_station_detail" not in result


async def test_update_fetches_charging_station_when_configured(ids_with_cs):
    api = MagicMock()
    api.get_rfid = AsyncMock(return_value={"rfid": {}, "status": {}})
    api.get_rfid_journal = AsyncMock(return_value=[])
    api.get_rfid_stats = AsyncMock(return_value={})
    api.get_charging_station_detail = AsyncMock(
        return_value={"status": {"car_plugged_in": True}}
    )

    result = await _make_coordinator(api, ids_with_cs)._async_update_data()

    api.get_charging_station_detail.assert_called_once_with(99)
    assert result["charging_station_detail"]["status"]["car_plugged_in"] is True


async def test_update_skips_charging_station_when_not_configured(ids_no_cs):
    api = MagicMock()
    api.get_rfid = AsyncMock(return_value={})
    api.get_rfid_journal = AsyncMock(return_value=[])
    api.get_rfid_stats = AsyncMock(return_value={})
    api.get_charging_station_detail = AsyncMock()

    await _make_coordinator(api, ids_no_cs)._async_update_data()

    api.get_charging_station_detail.assert_not_called()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

async def test_update_core_failure_propagates(ids_no_cs):
    api = MagicMock()
    api.get_rfid = AsyncMock(side_effect=RuntimeError("server down"))

    with pytest.raises(RuntimeError, match="server down"):
        await _make_coordinator(api, ids_no_cs)._async_update_data()


async def test_update_journal_failure_ignored(ids_no_cs):
    api = MagicMock()
    api.get_rfid = AsyncMock(return_value={"rfid": {}, "status": {}})
    api.get_rfid_journal = AsyncMock(side_effect=RuntimeError("journal broken"))
    api.get_rfid_stats = AsyncMock(return_value={})

    result = await _make_coordinator(api, ids_no_cs)._async_update_data()

    assert "journal" not in result


async def test_update_stats_failure_ignored(ids_no_cs):
    api = MagicMock()
    api.get_rfid = AsyncMock(return_value={"rfid": {}, "status": {}})
    api.get_rfid_journal = AsyncMock(return_value=[])
    api.get_rfid_stats = AsyncMock(side_effect=RuntimeError("stats broken"))

    result = await _make_coordinator(api, ids_no_cs)._async_update_data()

    assert "stats" not in result


async def test_update_charging_station_failure_ignored(ids_with_cs):
    api = MagicMock()
    api.get_rfid = AsyncMock(return_value={"rfid": {}, "status": {}})
    api.get_rfid_journal = AsyncMock(return_value=[])
    api.get_rfid_stats = AsyncMock(return_value={})
    api.get_charging_station_detail = AsyncMock(side_effect=RuntimeError("cs broken"))

    result = await _make_coordinator(api, ids_with_cs)._async_update_data()

    assert "charging_station_detail" not in result


# ---------------------------------------------------------------------------
# Date range params
# ---------------------------------------------------------------------------

async def test_journal_and_stats_called_with_30_day_window(ids_no_cs):
    api = MagicMock()
    api.get_rfid = AsyncMock(return_value={})
    api.get_rfid_journal = AsyncMock(return_value=[])
    api.get_rfid_stats = AsyncMock(return_value={})

    await _make_coordinator(api, ids_no_cs)._async_update_data()

    today = datetime.utcnow().date()
    start = (today - timedelta(days=30)).isoformat()
    end = today.isoformat()

    api.get_rfid_journal.assert_called_once_with(7, start, end)
    api.get_rfid_stats.assert_called_once_with(7, start, end, "day")
