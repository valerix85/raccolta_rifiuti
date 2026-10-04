# Creato da domoticafacile.it
"""Pure helpers (no Home Assistant objects) to read calendar events.

Kept separate from sensor.py so they can be unit-tested in isolation.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime, timedelta
import re
import unicodedata

from homeassistant.util import dt as dt_util

# Anything that is not a letter or a digit separates words: punctuation,
# emoji, parentheses, slashes, dashes...
_NON_WORD_RE = re.compile(r"[^\w]+", re.UNICODE)
# Words that only join several types in one summary ("Carta e Vetro").
_JOINERS = frozenset({"e", "ed", "and", "o", "or"})


def _strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch)
    )


def tokenize(text: str) -> list[str]:
    """Lower-case, accent-free list of words of `text`, joiners removed."""
    text = _strip_accents(text.casefold()).replace("_", " ")
    return [tok for tok in _NON_WORD_RE.split(text) if tok and tok not in _JOINERS]


class KeywordMatcher:
    """Find waste types in a free-text calendar summary (whole words only)."""

    def __init__(self, keywords: Mapping[str, Iterable[str]]) -> None:
        phrases: dict[tuple[str, ...], tuple[str, ...]] = {}
        for phrase, types in keywords.items():
            tokens = tuple(tokenize(phrase))
            if tokens:
                phrases[tokens] = tuple(types)
        self._phrases = phrases
        self._lengths = sorted({len(p) for p in phrases}, reverse=True)

    def match(self, summary: str) -> list[str]:
        """Return the types found in `summary` (in order, without duplicates)."""
        tokens = tokenize(summary)
        found: list[str] = []
        i = 0
        while i < len(tokens):
            for length in self._lengths:
                types = self._phrases.get(tuple(tokens[i : i + length]))
                if types is not None:
                    found.extend(t for t in types if t not in found)
                    i += length
                    break
            else:
                i += 1
        return found


def parse_event_time(value) -> tuple[datetime | None, bool]:
    """Return (local datetime, is_all_day) for a calendar start/end value."""
    if isinstance(value, datetime):
        return dt_util.as_local(value), False
    if isinstance(value, date):
        return dt_util.start_of_local_day(value), True
    if isinstance(value, str) and value:
        if "T" in value or " " in value:
            parsed = dt_util.parse_datetime(value)
            if parsed is not None:
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=dt_util.get_default_time_zone())
                return dt_util.as_local(parsed), False
        else:
            parsed_date = dt_util.parse_date(value)
            if parsed_date is not None:
                return dt_util.start_of_local_day(parsed_date), True
    return None, False


def event_days(start: datetime, end: datetime | None, first: date, last: date) -> list[date]:
    """Days in [first, last] covered by an event.

    An event covers a day when it overlaps it: e.g. an all-day event from
    Saturday to Monday (end exclusive) covers Saturday and Sunday. Events
    with a missing/invalid end only cover their start day.
    """
    start_day = start.date()
    if end is None or end <= start:
        end_day = start_day
    else:
        # `end` is exclusive: an event ending exactly at midnight does not
        # cover the following day.
        end_day = (end - timedelta(microseconds=1)).date()
    day = max(start_day, first)
    stop = min(end_day, last)
    days = []
    while day <= stop:
        days.append(day)
        day += timedelta(days=1)
    return days
