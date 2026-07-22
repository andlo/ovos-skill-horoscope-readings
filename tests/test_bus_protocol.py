"""Tests for the ovos.common_reading.* bus protocol handlers."""
from unittest.mock import MagicMock

from conftest import COMMON_READING_SEARCH_RESPONSE, COMMON_READING_FETCH_CONTENT_RESPONSE, COMMON_READING_PONG, HoroscopeFetchError


def make_message(data=None):
    m = MagicMock()
    m.data = data or {}
    m.reply = MagicMock(side_effect=lambda mtype, d: MagicMock(msg_type=mtype, data=d))
    return m


def test_handle_search_matches_sign_by_phrase(skill):
    skill.handle_search(make_message({"phrase": "leo horoscope"}))

    sent = skill.bus.emit.call_args[0][0]
    assert sent.msg_type == COMMON_READING_SEARCH_RESPONSE
    assert sent.data["content_id"] == "leo"
    assert sent.data["title"] == "Leo"
    assert sent.data["source"] == "freehoroscopeapi.com"
    assert sent.data["machine_translated"] is False


def test_handle_search_extra_words_dont_confuse_the_match(skill):
    """Regression guard: match_one()'s character-overlap scoring once
    picked 'Pisces' for the phrase 'leo horoscope' (higher incidental
    letter overlap than 'Leo'), before _match_sign()'s exact-word-first
    check was added."""
    for phrase in ["leo horoscope", "my leo horoscope", "horoscope for leo", "what does leo say today"]:
        skill.bus.emit.reset_mock()
        skill.handle_search(make_message({"phrase": phrase}))
        sent = skill.bus.emit.call_args[0][0]
        assert sent.data["content_id"] == "leo", f"failed for phrase: {phrase!r}"


def test_handle_search_no_phrase_declines_rather_than_guessing(skill):
    """The key design decision for this provider: unlike a story
    provider's 'surprise me', there's no valid arbitrary horoscope -
    the wrong sign is just wrong, not a fun surprise."""
    skill.handle_search(make_message({"phrase": None, "collection_hint": "horoscope"}))
    skill.bus.emit.assert_not_called()


def test_handle_search_stays_silent_for_unmatched_collection(skill):
    skill.handle_search(make_message({"phrase": "leo horoscope", "collection_hint": "tarot"}))
    skill.bus.emit.assert_not_called()


def test_handle_search_stays_silent_for_mismatched_content_type(skill):
    skill.handle_search(make_message({"phrase": "leo horoscope", "content_type": "story"}))
    skill.bus.emit.assert_not_called()


def test_handle_search_responds_for_matching_content_type(skill):
    for content_type in ["horoscope", "astrology", "HOROSCOPE"]:
        skill.bus.emit.reset_mock()
        skill.handle_search(make_message({"phrase": "leo horoscope", "content_type": content_type}))
        skill.bus.emit.assert_called_once()


def test_handle_fetch_content_success(skill):
    skill.get_horoscope_text = MagicMock(return_value="Today is a good day for Leos.")

    skill.handle_fetch_content(make_message({"content_id": "leo"}))

    sent = skill.bus.emit.call_args[0][0]
    assert sent.msg_type == COMMON_READING_FETCH_CONTENT_RESPONSE
    assert sent.data["paragraphs"] == ["Today is a good day for Leos."]


def test_handle_fetch_content_unknown_sign_returns_empty(skill):
    skill.handle_fetch_content(make_message({"content_id": "not-a-sign"}))
    sent = skill.bus.emit.call_args[0][0]
    assert sent.data["paragraphs"] == []


def test_handle_fetch_content_fetch_error_returns_empty(skill):
    skill.get_horoscope_text = MagicMock(side_effect=HoroscopeFetchError("boom"))

    skill.handle_fetch_content(make_message({"content_id": "leo"}))

    sent = skill.bus.emit.call_args[0][0]
    assert sent.data["paragraphs"] == []


def test_handle_ping_replies_with_pong(skill):
    skill.handle_ping(make_message())

    sent = skill.bus.emit.call_args[0][0]
    assert sent.msg_type == COMMON_READING_PONG
    assert sent.data["skill_id"] == skill.skill_id
    assert sent.data["collection"] == "Daily Horoscope"
