"""A request is answered in the language it was made in, not the device's.

On an en-us device with da-dk as a secondary language, "læs løvens
horoskop" reached the provider with phrase "løvens" and lang "da-DK", but
the sign names were the device language's ("Leo", "Pisces", ...), so the
Danish sign was not found. Found by the golden utterance run on a live
device."""
import pytest
from ovos_bus_client.message import Message

from conftest import COMMON_READING_SEARCH_RESPONSE, HoroscopeReadings


@pytest.fixture
def bilingual(skill, monkeypatch):
    monkeypatch.setattr(HoroscopeReadings, "native_langs", ["en-US", "da-DK"], raising=False)
    skill.bus.emit.reset_mock()
    return skill


def _search(skill, phrase, lang):
    skill.handle_search(Message("ovos.common_reading.search", {"phrase": phrase, "lang": lang}, {}))
    return skill.bus.emit.call_args[0][0]


@pytest.mark.parametrize("phrase,sign,title", [
    ("løven", "leo", "Løven"),
    ("løvens", "leo", "Løven"),          # genitive: "læs løvens horoskop"
    ("jomfruens horoskop", "virgo", "Jomfruen"),
    ("fiskenes", "pisces", "Fiskene"),
])
def test_danish_request_on_an_english_device(bilingual, phrase, sign, title):
    sent = _search(bilingual, phrase, "da-DK")
    assert sent.msg_type == COMMON_READING_SEARCH_RESPONSE
    assert sent.data["content_id"] == sign
    assert sent.data["title"] == title
    assert sent.data["confidence"] == 1.0
    assert sent.data["machine_translated"] is True


def test_english_request_still_uses_english_names(bilingual):
    sent = _search(bilingual, "leo", "en-US")
    assert sent.data["title"] == "Leo" and sent.data["machine_translated"] is False


def test_fetch_translates_to_the_language_asked_in(bilingual, monkeypatch):
    bilingual.index = {"leo": "Leo"}
    monkeypatch.setattr(bilingual, "get_horoscope_text", lambda sign: "A good day.", raising=False)
    asked = []
    monkeypatch.setattr(bilingual, "_maybe_translate_text",
                        lambda text, lang: (asked.append(lang), (text, True))[1], raising=False)
    bilingual.handle_fetch_content(Message("ovos.common_reading.fetch_content.x",
                                           {"content_id": "leo", "lang": "da-DK"}, {}))
    assert asked == ["da-DK"]
