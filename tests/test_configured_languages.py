"""This provider translates, but only answers in the languages the
installation is configured for (lang + secondary_langs), so a request in
any other language never loads a translation model."""
import pytest
from ovos_bus_client.message import Message

from conftest import HoroscopeReadings


def _request(msg_type, data):
    return Message(msg_type, data, {})


@pytest.fixture
def configured(skill, monkeypatch):
    monkeypatch.setattr(HoroscopeReadings, "native_langs", ["en-US", "da-DK"], raising=False)
    return skill


@pytest.mark.parametrize("lang, served", [
    ("en-US", True), ("da-DK", True), ("da", True), ("de-DE", False), ("fr-FR", False),
])
def test_serves_only_configured_languages(configured, lang, served):
    assert configured._serves(lang) is served


def test_search_in_an_unconfigured_language_gets_no_answer_and_no_translation(configured):
    configured._get_translator = lambda: (_ for _ in ()).throw(AssertionError("must not translate"))
    configured.bus.emit.reset_mock()
    configured.handle_search(_request("ovos.common_reading.search", {"phrase": "anything", "lang": "de-DE"}))
    configured.bus.emit.assert_not_called()


def test_ping_in_an_unconfigured_language_gets_no_pong(configured):
    configured.bus.emit.reset_mock()
    configured.handle_ping(_request("ovos.common_reading.ping", {"lang": "de-DE"}))
    configured.bus.emit.assert_not_called()
    configured.handle_ping(_request("ovos.common_reading.ping", {"lang": "da-DK"}))
    configured.bus.emit.assert_called_once()
