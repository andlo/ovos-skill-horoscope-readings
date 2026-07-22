"""Tests for the horoscope-text translation fallback (the actual daily
content - not the zodiac sign names, which are handled by
_get_zodiac_names() and tested separately)."""
from unittest.mock import MagicMock


def test_maybe_translate_text_skips_english(skill):
    text, translated = skill._maybe_translate_text("Today is good.", "en-us")
    assert text == "Today is good."
    assert translated is False


def test_maybe_translate_text_translates_non_english(skill, monkeypatch):
    fake_translator = MagicMock()
    fake_translator.translate.return_value = "I dag er en god dag."
    skill._get_translator = MagicMock(return_value=fake_translator)

    text, translated = skill._maybe_translate_text("Today is good.", "da-dk")

    assert text == "I dag er en god dag."
    assert translated is True
    fake_translator.translate.assert_called_once_with("Today is good.", target="da", source="en")


def test_maybe_translate_text_without_translator_stays_english(skill, monkeypatch):
    skill._get_translator = MagicMock(return_value=None)

    text, translated = skill._maybe_translate_text("Today is good.", "da-dk")

    assert text == "Today is good."
    assert translated is False


def test_maybe_translate_text_falls_back_on_translation_error(skill, monkeypatch):
    fake_translator = MagicMock()
    fake_translator.translate.side_effect = Exception("boom")
    skill._get_translator = MagicMock(return_value=fake_translator)

    text, translated = skill._maybe_translate_text("Today is good.", "da-dk")

    assert text == "Today is good."
    assert translated is False


def test_get_translator_caches_failure_without_retrying(skill, monkeypatch):
    import ovos_plugin_manager.language as lang_mod
    monkeypatch.setattr(
        lang_mod.OVOSLangTranslationFactory, "create",
        MagicMock(side_effect=Exception("no plugin configured"))
    )

    first = skill._get_translator()
    second = skill._get_translator()

    assert first is None
    assert second is None
    assert lang_mod.OVOSLangTranslationFactory.create.call_count == 1
