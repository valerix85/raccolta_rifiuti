# Creato da domoticafacile.it
"""Rule-based collection schedule (no Home Assistant objects, unit-testable).

Syntax of a rule string (one per waste type), comma separated tokens:

    lun              every Monday
    lun,ven          every Monday and Friday
    -mar             Tuesday of ODD weeks   (HassioHelp compatible: weeks are
    --mar            Tuesday of EVEN weeks   numbered from Monday like %W, the
                                             first week of January is even)
    4|1|mer          Wednesday of week 1 of a 4-week cycle (2..8 weeks),
                     cycle anchored on Monday 30/11/2020 (HassioHelp v1.0.b1)
    lun#1 / lun#ult  first / last Monday of the month (#1..#5, #ult)
    25/12            every 25th of December
    27/12/2026       one-off date (also 2026-12-27)

Day names: lun mar mer gio ven sab dom, full Italian names (with or
without accent) and English (mon, monday, ...). Case insensitive.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import re
import unicodedata

AXUREXIA_ANCHOR = date(2020, 11, 30)  # a Monday

_DAYS = {
    0: ("lun", "lunedi", "mon", "monday"),
    1: ("mar", "martedi", "tue", "tuesday"),
    2: ("mer", "mercoledi", "wed", "wednesday"),
    3: ("gio", "giovedi", "thu", "thursday"),
    4: ("ven", "venerdi", "fri", "friday"),
    5: ("sab", "sabato", "sat", "saturday"),
    6: ("dom", "domenica", "sun", "sunday"),
}
DAY_NAMES = {name: wd for wd, names in _DAYS.items() for name in names}
SHORT_DAY_IT = {wd: names[0] for wd, names in _DAYS.items()}
LAST = {"ult", "ultimo", "ultima", "last", "l", "-1"}

_RE_DATE_IT = re.compile(r"^(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{4}))?$")
_RE_DATE_ISO = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_RE_CYCLE = re.compile(r"^(\d+)\|(\d+)\|(\w+)$")
_RE_NTH = re.compile(r"^(\w+)#(\w+)$")
_RE_PARITY = re.compile(r"^(-{1,2})(\w+)$")


class RuleError(ValueError):
    """Invalid rule; str(err) is a human readable (Italian) message."""


@dataclass(frozen=True)
class Token:
    kind: str  # weekly | odd | even | cycle | nth | yearly | date
    weekday: int | None = None
    n: int = 0  # cycle length / nth occurrence (-1 = last)
    k: int = 0  # week of the cycle
    day: date | None = None  # for yearly: year ignored


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.strip().casefold())
    return "".join(c for c in text if not unicodedata.combining(c))


def _weekday(name: str, token: str) -> int:
    try:
        return DAY_NAMES[name]
    except KeyError:
        raise RuleError(f"giorno '{name}' non riconosciuto in '{token}' (usa lun, mar, mer, gio, ven, sab, dom)") from None


def parse_token(raw: str) -> Token:
    token = _norm(raw).replace(" ", "")
    if not token:
        raise RuleError("voce vuota")
    if m := _RE_DATE_ISO.match(token):
        try:
            return Token("date", day=date(int(m[1]), int(m[2]), int(m[3])))
        except ValueError:
            raise RuleError(f"data non valida '{raw}'") from None
    if m := _RE_DATE_IT.match(token):
        try:
            if m[3]:
                return Token("date", day=date(int(m[3]), int(m[2]), int(m[1])))
            return Token("yearly", day=date(2000, int(m[2]), int(m[1])))  # leap year
        except ValueError:
            raise RuleError(f"data non valida '{raw}'") from None
    if m := _RE_CYCLE.match(token):
        n, k = int(m[1]), int(m[2])
        if not 2 <= n <= 8 or not 1 <= k <= n:
            raise RuleError(f"'{raw}': il ciclo deve essere 2..8 settimane e la settimana 1..{n}")
        return Token("cycle", _weekday(m[3], raw), n=n, k=k)
    if m := _RE_NTH.match(token):
        wd = _weekday(m[1], raw)
        if m[2] in LAST:
            return Token("nth", wd, n=-1)
        if m[2].isdigit() and 1 <= int(m[2]) <= 5:
            return Token("nth", wd, n=int(m[2]))
        raise RuleError(f"'{raw}': dopo # usa 1..5 oppure ult")
    if m := _RE_PARITY.match(token):
        return Token("odd" if len(m[1]) == 1 else "even", _weekday(m[2], raw))
    return Token("weekly", _weekday(token, raw))


def parse_rule(rule: str | None) -> list[Token]:
    """Parse a full rule string. Empty string = never collected."""
    if not rule or not rule.strip():
        return []
    text = re.sub(r"\s*([|#/])\s*", r"\1", rule.strip())
    return [parse_token(part) for part in re.split(r"[,;\s]+", text) if part]


def validate_rule(rule: str | None) -> str | None:
    """Return None if valid, otherwise the error message."""
    try:
        parse_rule(rule)
    except RuleError as err:
        return str(err)
    return None


def token_matches(token: Token, day: date) -> bool:
    if token.kind == "date":
        return day == token.day
    if token.kind == "yearly":
        return (day.month, day.day) == (token.day.month, token.day.day)
    if day.weekday() != token.weekday:
        return False
    if token.kind == "weekly":
        return True
    if token.kind in ("odd", "even"):
        odd = int(day.strftime("%W")) % 2 == 1
        return odd if token.kind == "odd" else not odd
    if token.kind == "cycle":
        monday = day - timedelta(days=day.weekday())
        week = ((monday - AXUREXIA_ANCHOR).days // 7) % token.n + 1
        return week == token.k
    if token.kind == "nth":
        if token.n == -1:
            return (day + timedelta(days=7)).month != day.month
        return (day.day - 1) // 7 + 1 == token.n
    return False


def rule_matches(tokens: list[Token], day: date) -> bool:
    return any(token_matches(t, day) for t in tokens)


def build_schedule(
    rules: dict[str, list[Token]], start: date, days: int
) -> dict[date, list[str]]:
    """Collections from rules for start .. start+days-1 (only days with something)."""
    out: dict[date, list[str]] = {}
    for offset in range(days):
        day = start + timedelta(days=offset)
        codes = [code for code, tokens in rules.items() if rule_matches(tokens, day)]
        if codes:
            out[day] = codes
    return out


# ------------------------------------------------------------- exceptions

# A summary containing one of these words cancels instead of adding
# ("No umido", "Raccolta sospesa per sciopero", "Umido annullato").
_CANCEL_WORDS = (
    "no", "non", "niente", "nessuna", "nessun", "annullata", "annullato",
    "annullate", "annullati", "annulla", "sospesa", "sospeso", "sospese",
    "salta", "saltata", "saltato", "senza", "cancelled", "canceled", "skip",
)


def is_cancel(words: list[str]) -> bool:
    return any(word in _CANCEL_WORDS for word in words)


def apply_exception(
    current: list[str], matched: list[str], cancel: bool, all_types: list[str]
) -> list[str]:
    """Apply one exception event to the list of codes of a day."""
    if cancel:
        if not matched:  # "Nessuna raccolta" / "Sospesa" => cancel everything
            return []
        return [c for c in current if c not in matched]
    return current + [c for c in matched if c not in current]


def describe_rule(tokens: list[Token]) -> str:
    """Short Italian description, used in attributes."""
    parts = []
    for t in tokens:
        if t.kind == "weekly":
            parts.append(f"ogni {SHORT_DAY_IT[t.weekday]}")
        elif t.kind == "odd":
            parts.append(f"{SHORT_DAY_IT[t.weekday]} settimane dispari")
        elif t.kind == "even":
            parts.append(f"{SHORT_DAY_IT[t.weekday]} settimane pari")
        elif t.kind == "cycle":
            parts.append(f"{SHORT_DAY_IT[t.weekday]} settimana {t.k} di {t.n}")
        elif t.kind == "nth":
            nth = "ultimo" if t.n == -1 else f"{t.n}°"
            parts.append(f"{nth} {SHORT_DAY_IT[t.weekday]} del mese")
        elif t.kind == "yearly":
            parts.append(f"ogni {t.day.day:02d}/{t.day.month:02d}")
        elif t.kind == "date":
            parts.append(t.day.strftime("%d/%m/%Y"))
    return ", ".join(parts)
