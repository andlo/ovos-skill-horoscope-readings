# <img src='book-512.png' card_color='#40DBB0' width='50' height='50' style='vertical-align:bottom'/> Horoscope Readings (provider)

A *provider* skill for [ovos-common-reading-pipeline-plugin](https://github.com/andlo/ovos-common-reading-pipeline-plugin),
reading daily zodiac horoscopes aloud.

Sourced from [freehoroscopeapi.com](https://freehoroscopeapi.com/) - a
free, open REST API, no API key required.

[![Tests](https://github.com/andlo/ovos-skill-horoscope-readings/actions/workflows/test.yml/badge.svg)](https://github.com/andlo/ovos-skill-horoscope-readings/actions/workflows/test.yml)
[![PyPI version](https://img.shields.io/pypi/v/ovos-skill-horoscope-readings.svg)](https://pypi.org/project/ovos-skill-horoscope-readings/)

> **This skill has no standalone voice interface.** It registers no
> intents and never speaks. It only answers
> [ovos.common_reading.* bus messages](https://github.com/andlo/ovos-common-reading-pipeline-plugin#the-ovoscommon_reading-bus-protocol),
> so you also need **ovos-common-reading-pipeline-plugin** installed and
> added to your pipeline config for it to be useful at all.

## Install
```bash
pip install ovos-skill-horoscope-readings ovos-common-reading-pipeline-plugin
```

## How this provider is architecturally different

Every other provider in this family scrapes or fetches a list of
titles, caches it, and refreshes it periodically. This one doesn't -
the 12 zodiac signs never change, so they're the entire "index",
hardcoded and static. Only the actual horoscope *text* needs a live API
call, made fresh every time (no caching), since it's different every
day and the request is cheap and fast (a plain JSON REST call, no
scraping).

## Translation - two different mechanisms for two different things

**Only in configured languages.** It translates only into the languages
this installation is configured for: the device's own `lang` plus
`secondary_langs` in `mycroft.conf`. A search or ping in any other
language gets no answer, so a request in a language nobody here speaks
never loads a translation model or translates the title catalogue. A
HiveMind hub serving users in several languages lists them in
`secondary_langs`.

1. **Zodiac sign names** ("Leo", "Løven", "Löwe", "Lion", ...) - fixed,
   well-known, enumerable terms, bundled per-language in
   `locale/<lang>/zodiac_signs.json` rather than relying on a live
   translation plugin for individual out-of-context words (which risks
   poor-quality single-word translations). Falls back to the English
   names for any language without a bundled translation.
2. **The horoscope text itself** - genuinely dynamic daily content, so
   this *does* use live translation, same pattern as
   `ovos-skill-ovosblog`/`ovos-skill-arxiv-papers`/
   `ovos-skill-365tomorrows-stories`. Disclosed via
   `"machine_translated": true/false` in the search response.

Like those three translating providers, this one always loads
regardless of device language (no `SUPPORTED_LANGUAGES` gate) -
`collection_hint` aliases are loaded from `locale/<lang>/collection.voc`
with an English fallback for any language we haven't translated - see
[ovos-common-reading-pipeline-plugin#26](https://github.com/andlo/ovos-common-reading-pipeline-plugin/issues/26).

## No "surprise me"

Unlike a story provider, a search with a matching `collection_hint`
but no specific sign named **declines to respond** rather than picking
one at random - reading someone the wrong zodiac sign's horoscope isn't
a fun surprise, it's just wrong. You have to actually name a sign
("read me my Leo horoscope").

## Collection hints

Responds to `collection_hint` values in the *device's own language* -
e.g. "horoscope"/"zodiac"/"astrology" on English, "horoskop"/
"stjernetegn" on Danish - matched fuzzily against that language's own
alias list (see `locale/<lang>/collection.voc`).

## Content type

Identifies as `content_type: "horoscope"` or `"astrology"`. A search
with a `content_type` hint for anything else gets no response from this
provider.

## A regression worth knowing about

Early testing found `ovos_utils.parse.match_one()` picking **"Pisces"**
for the phrase *"leo horoscope"* - its character-overlap scoring got
confused by incidental shared letters once an extra word ("horoscope")
was in the phrase, the same class of false positive as "andrew lang"
scoring high against "andersen" elsewhere in this project. Fixed with
`_match_sign()`: since zodiac names are a small, fixed, single-word
vocabulary, an exact whole-word match is tried first, only falling back
to fuzzy `match_one()` for near-misses (e.g. a slightly misheard STT
transcription).

## Credits

Content sourced from [freehoroscopeapi.com](https://freehoroscopeapi.com/) -
free and open, no API key required.

## Category
**Entertainment**

## Tags
#horoscope #astrology #zodiac #provider

