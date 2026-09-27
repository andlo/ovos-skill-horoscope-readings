"""Tests for get_horoscope_text() against a mocked freehoroscopeapi.com
response (network calls aren't made in the test suite - see the real
live verification in the build notes/README instead)."""
from unittest.mock import MagicMock

import pytest
import requests
from conftest import HoroscopeFetchError


def _fake_response(json_data):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json = MagicMock(return_value=json_data)
    return r


def test_get_horoscope_text_success(skill, monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **kw: _fake_response(
        {"data": {"date": "2026-07-22", "sign": "Leo", "horoscope": "Today is a good day."}}
    ))

    text = skill.get_horoscope_text("leo")

    assert text == "Today is a good day."


def test_get_horoscope_text_passes_sign_param(skill, monkeypatch):
    captured = {}

    def fake_get(url, params=None, timeout=None, headers=None):
        captured["params"] = params
        return _fake_response({"data": {"horoscope": "..."}})

    monkeypatch.setattr(requests, "get", fake_get)
    skill.get_horoscope_text("pisces")

    assert captured["params"] == {"sign": "pisces"}


def test_get_horoscope_text_network_error_raises(skill, monkeypatch):
    def fail(*a, **kw):
        raise requests.ConnectionError("boom")
    monkeypatch.setattr(requests, "get", fail)

    with pytest.raises(HoroscopeFetchError):
        skill.get_horoscope_text("leo")


def test_get_horoscope_text_missing_horoscope_field_raises(skill, monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **kw: _fake_response({"data": {}}))

    with pytest.raises(HoroscopeFetchError):
        skill.get_horoscope_text("leo")


def test_get_horoscope_text_malformed_json_raises(skill, monkeypatch):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json = MagicMock(side_effect=ValueError("not json"))
    monkeypatch.setattr(requests, "get", lambda *a, **kw: r)

    with pytest.raises(HoroscopeFetchError):
        skill.get_horoscope_text("leo")
