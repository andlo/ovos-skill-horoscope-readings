"""Shared pytest fixtures for the horoscope-readings skill test suite."""
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_INIT_PATH = Path(__file__).resolve().parents[1] / "__init__.py"
_spec = importlib.util.spec_from_file_location("horoscope_skill", _INIT_PATH)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

HoroscopeReadings = _module.HoroscopeReadings
HoroscopeFetchError = _module.HoroscopeFetchError
ZODIAC_SIGNS = _module.ZODIAC_SIGNS
COMMON_READING_SEARCH_RESPONSE = _module.COMMON_READING_SEARCH_RESPONSE
COMMON_READING_FETCH_CONTENT_RESPONSE = _module.COMMON_READING_FETCH_CONTENT_RESPONSE
COMMON_READING_PONG = _module.COMMON_READING_PONG


@pytest.fixture
def skill(monkeypatch):
    s = HoroscopeReadings.__new__(HoroscopeReadings)
    s.log = MagicMock()
    s.skill_id = "ovos-skill-horoscope-readings.test"
    s.status = MagicMock()
    s._bus = MagicMock()
    s._settings = {}
    monkeypatch.setattr(HoroscopeReadings, "lang", "en-us", raising=False)
    monkeypatch.setattr(HoroscopeReadings, "native_langs", ["en-us"], raising=False)
    s.res_dir = str(Path(__file__).resolve().parents[1])  # repo root, holds locale/
    s._lang_resources = {}  # OVOSSkill.resources' internal per-language cache
    s._auto_register_entity_files = lambda *a, **k: None  # ovos-workshop >= 9.8 needs attributes __new__() bypasses
    s.index = {sign: sign for sign in ZODIAC_SIGNS}
    s._translator = None
    s._translator_failed = False
    # matches locale/en-us/collection.voc - most tests don't exercise
    # _load_collection_aliases() itself, they just need this
    # pre-populated the way initialize() would leave it
    s._collection_aliases = ["horoscope", "my horoscope", "daily horoscope", "star sign", "zodiac", "astrology"]
    return s
