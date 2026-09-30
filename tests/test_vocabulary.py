"""ovos.common_reading.vocabulary: what this provider tells the pipeline it
can read. Since pipeline 0.3.0 a request only reaches a provider whose
words (a kind of text, a collection or a title) it names."""
from ovos_bus_client.message import Message


def _sent(skill):
    return [c.args[0] for c in skill.bus.emit.call_args_list
            if c.args[0].msg_type == "ovos.common_reading.vocabulary"]

import pytest

from ovos_workshop.skills import OVOSSkill


@pytest.fixture
def configured(skill, monkeypatch):
    monkeypatch.setattr(type(skill), "native_langs", ["en-US", "da-DK"], raising=False)
    return skill


def test_vocabulary_per_language(configured):
    en = configured._vocabulary("en")
    da = configured._vocabulary("da")
    assert en["collections"] and da["collections"]
    assert en["content_types"] == {"horoscope": ["horoscope", "horoscopes", "astrology reading"]}
    assert "horoskop" in da["content_types"]["horoscope"]


def test_announced_for_every_configured_language(configured):
    configured._announce_vocabulary()
    assert [m.data["lang"] for m in _sent(configured)] == ["da", "en"]
    configured.bus.emit.reset_mock()
    configured.handle_vocabulary_get(Message("ovos.common_reading.vocabulary.get", {"langs": ["en-GB"]}))
    assert [m.data["lang"] for m in _sent(configured)] == ["en"]


def test_shutdown_takes_the_words_back(configured, monkeypatch):
    monkeypatch.setattr(OVOSSkill, "shutdown", lambda self: None)
    configured.shutdown()
    removed = [m for m in _sent(configured) if m.data.get("remove")]
    assert removed and removed[0].data["skill_id"] == configured.skill_id
