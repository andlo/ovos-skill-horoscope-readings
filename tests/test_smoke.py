"""Smoke tests + the static 12-sign index (no scraping/caching needed)."""
from conftest import HoroscopeReadings, HoroscopeFetchError, ZODIAC_SIGNS


def test_imports_cleanly():
    assert HoroscopeReadings is not None
    assert issubclass(HoroscopeFetchError, Exception)


def test_is_an_ovos_skill():
    from ovos_workshop.skills import OVOSSkill
    assert issubclass(HoroscopeReadings, OVOSSkill)


def test_all_twelve_signs_present():
    assert len(ZODIAC_SIGNS) == 12
    assert len(set(ZODIAC_SIGNS)) == 12  # no duplicates
