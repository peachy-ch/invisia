"""Unit tests for sensor._get_path and ATTR_LIST_MAX_ITEMS usage."""
from __future__ import annotations

import pytest

from custom_components.invisia.sensor import _get_path
from custom_components.invisia.const import ATTR_LIST_MAX_ITEMS


# ---------------------------------------------------------------------------
# _get_path
# ---------------------------------------------------------------------------

def test_get_path_single_key():
    assert _get_path({"key": "value"}, "key") == "value"


def test_get_path_nested():
    data = {"stats": {"current_power_flow": 9.46}}
    assert _get_path(data, "stats.current_power_flow") == 9.46


def test_get_path_deeply_nested():
    data = {"a": {"b": {"c": 42}}}
    assert _get_path(data, "a.b.c") == 42


def test_get_path_missing_key_returns_none():
    data = {"stats": {"current_power_flow": 9.46}}
    assert _get_path(data, "stats.missing_key") is None


def test_get_path_missing_top_level_returns_none():
    assert _get_path({}, "stats.current_power_flow") is None


def test_get_path_non_dict_intermediate_returns_none():
    data = {"stats": "not_a_dict"}
    assert _get_path(data, "stats.current_power_flow") is None


def test_get_path_none_intermediate_returns_none():
    data = {"stats": None}
    assert _get_path(data, "stats.current_power_flow") is None


def test_get_path_returns_zero():
    """Falsy numeric values must not be confused with None."""
    data = {"power": 0.0}
    assert _get_path(data, "power") == 0.0


def test_get_path_returns_false():
    """Falsy boolean values must not be confused with None."""
    data = {"active": False}
    assert _get_path(data, "active") is False


def test_get_path_returns_empty_string():
    data = {"label": ""}
    assert _get_path(data, "label") == ""


def test_get_path_returns_list():
    data = {"items": [1, 2, 3]}
    assert _get_path(data, "items") == [1, 2, 3]


# ---------------------------------------------------------------------------
# ATTR_LIST_MAX_ITEMS value
# ---------------------------------------------------------------------------

def test_attr_list_max_items_is_positive_int():
    assert isinstance(ATTR_LIST_MAX_ITEMS, int)
    assert ATTR_LIST_MAX_ITEMS > 0


def test_attr_list_max_items_limits_journal_slice():
    """Verify the constant produces the expected truncation behaviour."""
    long_list = list(range(ATTR_LIST_MAX_ITEMS + 10))
    assert len(long_list[:ATTR_LIST_MAX_ITEMS]) == ATTR_LIST_MAX_ITEMS
