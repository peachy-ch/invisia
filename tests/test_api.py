"""Unit tests for api.py."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from conftest import make_response


# ---------------------------------------------------------------------------
# login()
# ---------------------------------------------------------------------------

async def test_login_success(mock_session):
    from custom_components.invisia.api import InvisiaAPI

    resp = make_response(json_data={"access": "acc123", "refresh": "ref456"})
    mock_session.post = AsyncMock(return_value=resp)

    api = InvisiaAPI("u@example.com", "pw", "1", mock_session)
    await api.login()

    assert api._access_token == "acc123"
    assert api._refresh_token == "ref456"


async def test_login_invalid_credentials_raises(mock_session):
    from custom_components.invisia.api import InvisiaAPI

    resp = make_response(json_data={"detail": "no token for you"})
    mock_session.post = AsyncMock(return_value=resp)

    api = InvisiaAPI("bad@example.com", "wrongpw", "1", mock_session)
    with pytest.raises(RuntimeError, match="no access token"):
        await api.login()


# ---------------------------------------------------------------------------
# refresh()
# ---------------------------------------------------------------------------

async def test_refresh_success(api, mock_session):
    resp = make_response(json_data={"access": "new_acc", "refresh": "new_ref"})
    mock_session.post = AsyncMock(return_value=resp)

    await api.refresh()

    assert api._access_token == "new_acc"
    assert api._refresh_token == "new_ref"


async def test_refresh_falls_back_to_login_when_no_refresh_token(api, mock_session):
    api._refresh_token = None
    resp = make_response(json_data={"access": "login_acc", "refresh": "login_ref"})
    mock_session.post = AsyncMock(return_value=resp)

    await api.refresh()

    assert api._access_token == "login_acc"


# ---------------------------------------------------------------------------
# _request() – 429 retry
# ---------------------------------------------------------------------------

async def test_request_retries_on_429(api, mock_session):
    rate_resp = make_response(status=429, json_data={"detail": "throttled"})
    ok_resp = make_response(status=200, json_data={"profile": "instant"})
    mock_session.request = AsyncMock(side_effect=[rate_resp, ok_resp])

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await api._request("GET", "/api/cockpit/installations/42/rfids/7")

    assert result == {"profile": "instant"}
    assert mock_session.request.call_count == 2


async def test_request_raises_after_max_retries_on_429(api, mock_session):
    from custom_components.invisia.api import _MAX_RETRIES

    rate_resp = make_response(status=429, json_data={"detail": "throttled"})
    mock_session.request = AsyncMock(return_value=rate_resp)

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(RuntimeError, match="rate limited"):
            await api._request("GET", "/api/cockpit/installations/42/rfids/7")

    assert mock_session.request.call_count == _MAX_RETRIES + 1


async def test_request_respects_retry_after_header(api, mock_session):
    rate_resp = make_response(status=429, json_data={"detail": "throttled"})
    rate_resp.headers = {"Retry-After": "10"}
    ok_resp = make_response(status=200, json_data={"ok": True})
    mock_session.request = AsyncMock(side_effect=[rate_resp, ok_resp])

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await api._request("GET", "/some/path")

    mock_sleep.assert_called_once_with(10)


# ---------------------------------------------------------------------------
# _request() – non-JSON handling
# ---------------------------------------------------------------------------

async def test_request_non_json_allowed_returns_stub(api, mock_session):
    resp = make_response(
        status=200, text_data="<html>oops</html>", raise_content_type=True
    )
    mock_session.request = AsyncMock(return_value=resp)

    result = await api._request("GET", "/some/path", allow_non_json=True)

    assert result["_non_json"] is True
    assert result["status"] == 200
    assert "oops" in result["text"]


async def test_request_non_json_raises_when_not_allowed(api, mock_session):
    resp = make_response(
        status=200, text_data="<html>oops</html>", raise_content_type=True
    )
    mock_session.request = AsyncMock(return_value=resp)

    with pytest.raises(RuntimeError, match="non-JSON"):
        await api._request("GET", "/some/path", allow_non_json=False)


# ---------------------------------------------------------------------------
# _request() – token auto-refresh
# ---------------------------------------------------------------------------

async def test_request_refreshes_token_on_token_not_valid(api, mock_session):
    expired_resp = make_response(status=401, json_data={"code": "token_not_valid"})
    ok_resp = make_response(status=200, json_data={"profile": "instant"})
    refresh_resp = make_response(
        json_data={"access": "refreshed_token", "refresh": "ref2"}
    )

    mock_session.request = AsyncMock(side_effect=[expired_resp, ok_resp])
    mock_session.post = AsyncMock(return_value=refresh_resp)

    result = await api._request("GET", "/api/cockpit/installations/42/rfids/7")

    assert result == {"profile": "instant"}
    assert api._access_token == "refreshed_token"
    assert mock_session.request.call_count == 2


# ---------------------------------------------------------------------------
# _request() – 4xx API error
# ---------------------------------------------------------------------------

async def test_request_raises_on_4xx_json_error(api, mock_session):
    resp = make_response(status=404, json_data={"detail": "not found"})
    mock_session.request = AsyncMock(return_value=resp)

    with pytest.raises(RuntimeError, match="404"):
        await api._request("GET", "/api/nope")


# ---------------------------------------------------------------------------
# _request() – happy path 200
# ---------------------------------------------------------------------------

async def test_request_returns_data_on_success(api, mock_session):
    resp = make_response(status=200, json_data={"key": "value"})
    mock_session.request = AsyncMock(return_value=resp)

    result = await api._request("GET", "/api/something")

    assert result == {"key": "value"}


# ---------------------------------------------------------------------------
# _request() – error bodies must never be returned as payloads
# ---------------------------------------------------------------------------

async def test_request_raises_on_non_json_error_body(api, mock_session):
    """A 404 HTML page used to come back as {"_non_json": True, "status": 404}.

    That sentinel's "status" key shadows the status object every entity reads,
    so detail["status"].get(...) hit an int and raised inside the state write.
    """
    resp = make_response(status=404, text_data="<html>not found</html>", raise_content_type=True)
    mock_session.request = AsyncMock(return_value=resp)

    with pytest.raises(RuntimeError, match="404"):
        await api._request("GET", "/api/something", allow_non_json=True)


async def test_request_raises_on_5xx_non_json_even_when_allowed(api, mock_session):
    resp = make_response(status=503, text_data="gateway down", raise_content_type=True)
    mock_session.request = AsyncMock(return_value=resp)

    with pytest.raises(RuntimeError, match="503"):
        await api._request("GET", "/api/something", allow_non_json=True)


async def test_request_raises_on_4xx_json_list_body(api, mock_session):
    resp = make_response(status=403, json_data=["forbidden"])
    mock_session.request = AsyncMock(return_value=resp)

    with pytest.raises(RuntimeError, match="403"):
        await api._request("GET", "/api/something")


async def test_non_json_sentinel_still_returned_for_2xx(api, mock_session):
    """PATCH replies with an empty/HTML body are normal and must not raise."""
    resp = make_response(status=204, text_data="", raise_content_type=True)
    mock_session.request = AsyncMock(return_value=resp)

    result = await api._request("PATCH", "/api/something", allow_non_json=True)

    assert result["_non_json"] is True
    assert result["status"] == 204


# ---------------------------------------------------------------------------
# get_charging_station_detail() – RFID-only installations
# ---------------------------------------------------------------------------

async def test_charging_station_detail_empty_404_returns_empty_dict(api, mock_session):
    resp = make_response(status=404, text_data="", raise_content_type=True)
    mock_session.request = AsyncMock(return_value=resp)

    assert await api.get_charging_station_detail("99") == {}


async def test_charging_station_detail_json_404_returns_empty_dict(api, mock_session):
    resp = make_response(status=404, json_data={"detail": "not found"})
    mock_session.request = AsyncMock(return_value=resp)

    assert await api.get_charging_station_detail("99") == {}


async def test_charging_station_detail_returns_payload_when_present(api, mock_session):
    resp = make_response(status=200, json_data={"status": {"car_plugged_in": True}})
    mock_session.request = AsyncMock(return_value=resp)

    result = await api.get_charging_station_detail("99")

    assert result["status"]["car_plugged_in"] is True


async def test_charging_station_detail_500_still_raises(api, mock_session):
    resp = make_response(status=500, text_data="boom", raise_content_type=True)
    mock_session.request = AsyncMock(return_value=resp)

    with pytest.raises(RuntimeError, match="500"):
        await api.get_charging_station_detail("99")
