"""Tests for _load_collection_aliases() - same fallback pattern as
ovos-skill-ovosblog/ovos-skill-arxiv-papers/
ovos-skill-365tomorrows-stories."""
import pytest


@pytest.mark.parametrize("lang", ["en-us", "da-dk", "de-de", "es-es", "fr-fr", "it-it", "nl-nl", "pt-pt"])
def test_load_collection_aliases_per_language(skill, monkeypatch, lang):
    monkeypatch.setattr(type(skill), "lang", lang, raising=False)

    skill._load_collection_aliases()

    assert len(skill._collection_aliases) > 0


def test_danish_alias_matches_danish_phrasing(skill, monkeypatch):
    monkeypatch.setattr(type(skill), "lang", "da-dk", raising=False)
    skill._load_collection_aliases()

    assert skill._matches_collection_hint("stjernetegn") is True


def test_falls_back_to_english_for_untranslated_language(skill, monkeypatch):
    monkeypatch.setattr(type(skill), "lang", "ja-jp", raising=False)

    skill._load_collection_aliases()

    assert skill._collection_aliases == [
        "horoscope", "my horoscope", "daily horoscope", "star sign", "zodiac", "astrology"
    ]
