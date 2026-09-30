"""
skill OVOS Horoscope Readings
Copyright (C) 2026  Andreas Lorensen

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

---

Provider skill for ovos-common-reading-pipeline-plugin: reads daily
zodiac horoscopes aloud (content_type: "horoscope"). Source is
freehoroscopeapi.com - a free, open, no-API-key-required REST API
(https://freehoroscopeapi.com), not an RSS feed like most other
providers in this family.

Architecturally different from every other provider so far: there's no
scraped/fetched "index" of titles to build and cache - the 12 zodiac
signs ARE the index, and they never change. Only the actual horoscope
TEXT needs a live per-request API call (it's different every day), so
there's no refresh_index()/INDEX_CACHE_TTL machinery here at all.

Two separate translation concerns, handled two different ways:
1. Zodiac sign NAMES ("Leo", "Løven", "Löwe", ...) - fixed, well-known,
   enumerable terms. Bundled per-language in
   locale/<lang>/zodiac_signs.json rather than relying on a live
   translation plugin for single out-of-context words (which risks
   poor-quality single-word translations) - same reasoning as
   ovos-skill-andersen-tales/ovos-skill-grimm-tales's
   collection_meta.json pattern, just for a fixed 12-item vocabulary
   instead of one author/collection name.
2. The horoscope TEXT itself - genuinely dynamic daily content, so this
   DOES use live translation, same pattern as ovos-skill-ovosblog/
   ovos-skill-arxiv-papers/ovos-skill-365tomorrows-stories.

Like those three, this provider always loads regardless of device
language (no SUPPORTED_LANGUAGES gate) - collection_hint aliases are
loaded from locale/<lang>/collection.voc with an English fallback, see
ovos-common-reading-pipeline-plugin#26.
"""

from ovos_workshop.skills import OVOSSkill
from ovos_bus_client.session import SessionManager
from ovos_bus_client.message import Message
from pathlib import Path
from ovos_utils.parse import match_one
from ovos_utils import classproperty
from ovos_utils.process_utils import RuntimeRequirements

import requests
import json
import re


def _user_agent():
    """Say who is asking. Some sites answer python-requests' default
    User-Agent with 403 (365tomorrows.com behind Cloudflare does), and a
    descriptive one is what sites ask automated clients to send."""
    try:
        from importlib.metadata import version
        ver = version("ovos-skill-horoscope-readings")
    except Exception:
        ver = "unknown"
    return f"ovos-skill-horoscope-readings/{ver} (+https://github.com/andlo/ovos-skill-horoscope-readings)"


HTTP_HEADERS = {"User-Agent": _user_agent()}


def _read_voc(path):
    """Phrases in a .voc file: one per line, "a|b" and "(a|b) c" expanded
    the simple way ovos-workshop does for single groups."""
    phrases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(.*)\(([^)]*)\)(.*)$", line)
        if m:
            phrases += [" ".join(f"{m.group(1)}{alt}{m.group(3)}".split()) for alt in m.group(2).split("|")]
        else:
            phrases += [alt.strip() for alt in line.split("|") if alt.strip()]
    return phrases


class HoroscopeFetchError(Exception):
    """Raised when the horoscope API could not be reached or returned
    something unusable."""


COMMON_READING_SEARCH = "ovos.common_reading.search"
COMMON_READING_SEARCH_RESPONSE = "ovos.common_reading.search.response"
COMMON_READING_FETCH_CONTENT = "ovos.common_reading.fetch_content"  # + ".{this_skill_id}"
COMMON_READING_FETCH_CONTENT_RESPONSE = "ovos.common_reading.fetch_content.response"
COMMON_READING_PING = "ovos.common_reading.ping"
COMMON_READING_PONG = "ovos.common_reading.pong"
# vocabulary: the words people use for what this provider can read, one
# message per language it serves - announced when it loads and whenever
# the pipeline asks (see the pipeline plugin's README, "4. Vocabulary").
# Without it the pipeline (0.3.0+) never sends a request here.
COMMON_READING_VOCABULARY = "ovos.common_reading.vocabulary"
COMMON_READING_VOCABULARY_GET = "ovos.common_reading.vocabulary.get"

HOROSCOPE_API_URL = "https://freehoroscopeapi.com/api/v1/get-horoscope/daily"
ZODIAC_SIGNS = ["aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra",
                "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]

# this provider translates and works on ANY device language - see
# ovos-common-reading-pipeline-plugin#26. Only used as a fallback for
# any language without a locale/<lang>/collection.voc translation.
FALLBACK_COLLECTION_ALIASES = ["horoscope", "my horoscope", "daily horoscope", "star sign", "zodiac", "astrology"]
CONTENT_TYPES = ["horoscope", "astrology"]
COLLECTION_HINT_THRESHOLD = 0.85
COLLECTION_NAME = "Daily Horoscope"
SOURCE_NAME = "freehoroscopeapi.com"


def primary_subtag(lang):
    """'en-US', 'en_gb', 'EN' -> 'en'."""
    return (lang or "").replace("_", "-").split("-")[0].lower()


def configured_languages(langs):
    """Primary subtags of the languages an installation is configured
    for (core lang + secondary_langs): ['en-US', 'da-DK'] -> {'en', 'da'}."""
    return {primary_subtag(lang) for lang in langs or [] if lang}

class HoroscopeReadings(OVOSSkill):

    @classproperty
    def runtime_requirements(self):
        return RuntimeRequirements(
            internet_before_load=True,
            network_before_load=True,
            requires_internet=True,
            requires_network=True,
            no_internet_fallback=True,
            no_network_fallback=True,
        )

    def initialize(self):
        # the 12 signs never change - no scraping, no cache, no
        # refresh_index() needed, unlike every other provider here
        self.index = {sign: sign for sign in ZODIAC_SIGNS}
        self._translator = None
        self._translator_failed = False
        self._load_collection_aliases()
        self.add_event(COMMON_READING_SEARCH, self.handle_search)
        self.add_event(f"{COMMON_READING_FETCH_CONTENT}.{self.skill_id}", self.handle_fetch_content)
        self.add_event(COMMON_READING_PING, self.handle_ping)
        self.add_event(COMMON_READING_VOCABULARY_GET, self.handle_vocabulary_get)
        self._announce_vocabulary()

    def _load_collection_aliases(self):
        """Same pattern as ovos-skill-ovosblog: loads
        locale/<lang>/collection.voc for the current device language,
        falling back to FALLBACK_COLLECTION_ALIASES (English) for any
        language we haven't bothered translating."""
        aliases_raw = self.resources.load_vocabulary_file("collection")
        aliases = [phrase for line in aliases_raw for phrase in line]
        self._collection_aliases = aliases or FALLBACK_COLLECTION_ALIASES

    def _get_zodiac_names(self, lang):
        """Bundled per-language sign names (see module docstring for
        why this is a curated resource file rather than a live
        translation call) - falls back to the English names for any
        language we haven't bundled a translation for.
        load_json_file() returns {} (not an exception) when the file
        isn't found, so the fallback below covers that case too."""
        names = self.resources.load_json_file("zodiac_signs.json")
        return names or {sign: sign.capitalize() for sign in ZODIAC_SIGNS}

    def get_horoscope_text(self, sign):
        """Live API call - no caching, since the text is different
        every day and the request is cheap/fast (unlike scraping)."""
        try:
            r = requests.get(HOROSCOPE_API_URL, params={"sign": sign}, timeout=10, headers=HTTP_HEADERS)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            raise HoroscopeFetchError(f"failed to fetch horoscope for '{sign}': {e}") from e
        except ValueError as e:
            raise HoroscopeFetchError(f"could not parse horoscope response for '{sign}': {e}") from e
        text = data.get("data", {}).get("horoscope")
        if not text:
            raise HoroscopeFetchError(f"no horoscope text in response for '{sign}'")
        return text

    def _get_translator(self):
        if self._translator is None and not self._translator_failed:
            try:
                from ovos_plugin_manager.language import OVOSLangTranslationFactory
                self._translator = OVOSLangTranslationFactory.create()
            except Exception as e:
                self.log.warning(f"no language translation plugin available: {e}")
                self._translator_failed = True
        return self._translator

    def _maybe_translate_text(self, text, lang):
        target = lang.split("-")[0]
        if target == "en":
            return text, False
        translator = self._get_translator()
        if translator is None:
            return text, False
        try:
            return translator.translate(text, target=target, source="en"), True
        except Exception as e:
            self.log.warning(f"translation failed, falling back to English: {e}")
            return text, False

    def _matches_collection_hint(self, hint):
        if not hint:
            return True
        _, score = match_one(hint.lower(), self._collection_aliases)
        return score >= COLLECTION_HINT_THRESHOLD

    def _matches_content_type(self, content_type):
        if not content_type:
            return True
        return content_type.lower() in CONTENT_TYPES

    def _match_sign(self, phrase, names):
        """Zodiac sign names are a small, fixed vocabulary of single
        words - check for an exact whole-word match first. This is a
        real regression fix: match_one()'s character-overlap scoring
        gets confused by extra words in the phrase (e.g. 'leo
        horoscope' scored higher against 'Pisces' than 'Leo', purely
        from incidental shared letters - the same class of false
        positive as 'andrew lang' vs 'andersen' noted elsewhere in this
        project). Falls back to fuzzy match_one only if no exact word
        match is found (e.g. a slightly misheard STT transcription)."""
        phrase_words = re.findall(r"\w+", phrase.lower())
        for sign, name in names.items():
            if name.lower() in phrase_words:
                return name, 1.0
        return match_one(phrase, list(names.values()))


    @staticmethod
    def _request_lang(message):
        """The language a request was made in, or None when it does not
        say: the pipeline plugin's own 'lang' field first, then the
        language of the session the request was forwarded from (a
        HiveMind client's, on a hub). An older plugin sends neither."""
        lang = message.data.get("lang") or message.context.get("lang")
        if not lang and message.context.get("session"):
            lang = SessionManager.get(message).lang
        return lang or None

    def _serves(self, lang):
        """This provider translates, so it could answer in any language -
        but it only does for the languages this installation is
        configured for (the device's lang plus secondary_langs in
        mycroft.conf). A request in any other language would otherwise
        load a translation model and translate the whole catalogue of
        titles for a language nobody here speaks."""
        return primary_subtag(lang) in configured_languages(self.native_langs)

    def handle_search(self, message):
        if not self._serves(self._request_lang(message) or self.lang):
            return  # not a language this installation is configured for
        collection_hint = message.data.get("collection_hint")
        if not self._matches_collection_hint(collection_hint):
            return
        content_type = message.data.get("content_type")
        if not self._matches_content_type(content_type):
            return

        names = self._get_zodiac_names(self.lang)
        phrase = message.data.get("phrase")
        if not phrase:
            # unlike a story provider's 'surprise me', there's no such
            # thing as a valid arbitrary horoscope - reading someone
            # the wrong sign's horoscope isn't a fun surprise, it's just
            # wrong. Decline rather than guess a sign.
            return
        title, confidence = self._match_sign(phrase, names)
        sign = next(s for s, name in names.items() if name == title)

        self.bus.emit(message.reply(COMMON_READING_SEARCH_RESPONSE, {
            "skill_id": self.skill_id,
            "content_id": sign,
            "title": title,
            "collection": COLLECTION_NAME,
            "source": SOURCE_NAME,
            "confidence": confidence,
            "machine_translated": self.lang.split("-")[0] != "en",
        }))

    def handle_fetch_content(self, message):
        sign = message.data.get("content_id")
        if sign not in self.index:
            self.bus.emit(message.reply(COMMON_READING_FETCH_CONTENT_RESPONSE, {"paragraphs": []}))
            return
        try:
            text = self.get_horoscope_text(sign)
        except HoroscopeFetchError as e:
            self.log.error(f"Could not fetch horoscope for '{sign}': {e}")
            self.bus.emit(message.reply(COMMON_READING_FETCH_CONTENT_RESPONSE, {"paragraphs": []}))
            return
        text, _ = self._maybe_translate_text(text, self.lang)
        self.bus.emit(message.reply(COMMON_READING_FETCH_CONTENT_RESPONSE, {"paragraphs": [text]}))

    def _vocabulary_langs(self):
        return sorted(configured_languages(self.native_langs))

    def _locale_words(self, name, lang):
        """The phrases of locale/<lang>/<name>.voc for a primary language
        tag ("da"), or [] when this skill has no such file for it."""
        base = Path(__file__).resolve().parent / "locale"
        for folder in sorted(base.iterdir()) if base.is_dir() else []:
            if folder.name.split("-")[0] == lang and (folder / f"{name}.voc").is_file():
                return _read_voc(folder / f"{name}.voc")
        return []

    def _vocabulary(self, lang):
        """The kind of text this provider serves (locale/<lang>/content_type.voc,
        announced under its canonical name CONTENT_TYPES[0]) and its
        collection names (collection.voc) in `lang`. No titles: they change
        daily and are only known in the source's own language."""
        words = self._locale_words("content_type", lang)
        return {"content_types": {CONTENT_TYPES[0]: words} if words else {},
                "collections": self._locale_words("collection", lang) or list(FALLBACK_COLLECTION_ALIASES)}

    def _announce_vocabulary(self, langs=None, message=None):
        """One ovos.common_reading.vocabulary per language served (and
        asked for, when the pipeline named languages)."""
        wanted = {str(l).lower().split("-")[0].split("_")[0] for l in (langs or [])}
        for lang in self._vocabulary_langs():
            if wanted and lang not in wanted:
                continue
            data = {"skill_id": self.skill_id, "lang": lang, **self._vocabulary(lang)}
            msg = message.reply(COMMON_READING_VOCABULARY, data) if message else \
                Message(COMMON_READING_VOCABULARY, data)
            self.bus.emit(msg)

    def handle_vocabulary_get(self, message):
        self._announce_vocabulary(message.data.get("langs"), message)

    def shutdown(self):
        """The pipeline stops sending requests meant for this provider."""
        try:
            self.bus.emit(Message(COMMON_READING_VOCABULARY, {"skill_id": self.skill_id, "remove": True}))
        except Exception:
            pass
        super().shutdown()

    def handle_ping(self, message):
        """Cheap 'is anyone there?' reply - no API call. Only ever
        called by the pipeline plugin on its rare 0-candidates path
        (see ovos-common-reading-pipeline-plugin#2), never on every
        search."""
        lang = self._request_lang(message)
        if lang and not self._serves(lang):
            return
        self.bus.emit(message.reply(COMMON_READING_PONG, {
            "skill_id": self.skill_id,
            "collection": COLLECTION_NAME,
        }))
