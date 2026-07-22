"""Tests for _get_zodiac_names() against the real locale/<lang>/
zodiac_signs.json files - not mocks, since the point is verifying the
actual bundled translations parse correctly for every supported
language."""
import pytest


@pytest.mark.parametrize("lang,expected_leo", [
    ("en-us", "Leo"), ("da-dk", "Løven"), ("de-de", "Löwe"), ("es-es", "Leo"),
    ("fr-fr", "Lion"), ("it-it", "Leone"), ("nl-nl", "Leeuw"), ("pt-pt", "Leão"),
])
def test_zodiac_names_per_language(skill, monkeypatch, lang, expected_leo):
    monkeypatch.setattr(type(skill), "lang", lang, raising=False)

    names = skill._get_zodiac_names(lang)

    assert len(names) == 12
    assert names["leo"] == expected_leo


def test_falls_back_to_english_for_untranslated_language(skill, monkeypatch):
    """Japanese has no locale/ja-jp/zodiac_signs.json and no close
    relative to fall back to via langcodes."""
    monkeypatch.setattr(type(skill), "lang", "ja-jp", raising=False)

    names = skill._get_zodiac_names("ja-jp")

    assert names["leo"] == "Leo"
    assert names["pisces"] == "Pisces"
