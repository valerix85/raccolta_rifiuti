# Creato da domoticafacile.it
"""Coordinator for the UI (config entry) mode: rules + exception calendar."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
import logging

from homeassistant.components.calendar import DOMAIN as CALENDAR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import CONF_EXCEPTIONS_CALENDAR, CONF_RULES, DOMAIN, HORIZON_DAYS
from .localization import TYPE_ORDER, build_keyword_index
from .parser import KeywordMatcher, event_days, parse_event_time, tokenize
from .schedule import RuleError, Token, apply_exception, build_schedule, is_cancel, parse_rule

_LOGGER = logging.getLogger(__name__)
_RANK = {code: i for i, code in enumerate(TYPE_ORDER)}


def sort_codes(codes) -> list[str]:
    return sorted(set(codes), key=lambda c: (_RANK.get(c, 99), c))


@dataclass
class ScheduleData:
    today: date
    days: dict[date, list[str]] = field(default_factory=dict)
    exceptions: dict[date, list[str]] = field(default_factory=dict)
    exceptions_ok: bool = True

    def on(self, day: date) -> list[str]:
        return self.days.get(day, [])

    def next_collection(self, start: date) -> tuple[date | None, list[str]]:
        for day in sorted(d for d in self.days if d >= start):
            return day, self.days[day]
        return None, []

    def next_dates(self, code: str, start: date, limit: int = 5) -> list[date]:
        return [d for d in sorted(self.days) if d >= start and code in self.days[d]][:limit]


class RaccoltaCoordinator(DataUpdateCoordinator[ScheduleData]):
    """Computes the collections for today .. today + HORIZON_DAYS."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=timedelta(minutes=30),
        )
        self.matcher = KeywordMatcher(build_keyword_index())
        self.rules: dict[str, list[Token]] = {}
        self.rule_text: dict[str, str] = {}
        self.load_options()

    # ----------------------------------------------------------- options
    def load_options(self) -> None:
        options = self.config_entry.options
        self.calendar_id: str | None = options.get(CONF_EXCEPTIONS_CALENDAR) or None
        rules: dict[str, list[Token]] = {}
        texts: dict[str, str] = {}
        for code, text in (options.get(CONF_RULES) or {}).items():
            texts[code] = text or ""
            try:
                rules[code] = parse_rule(text)
            except RuleError as err:  # should not happen: validated on input
                _LOGGER.error("Regola non valida per %s ('%s'): %s", code, text, err)
                rules[code] = []
        self.rules = {code: tokens for code, tokens in rules.items() if tokens}
        self.rule_text = texts

    @property
    def active_types(self) -> list[str]:
        return sort_codes(self.rules)

    # ---------------------------------------------------------- listeners
    @callback
    def async_setup_listeners(self) -> None:
        @callback
        def _refresh(*_args) -> None:
            self.hass.async_create_task(self.async_request_refresh())

        self.config_entry.async_on_unload(
            async_track_time_change(self.hass, _refresh, hour=0, minute=0, second=5)
        )
        if self.calendar_id:

            @callback
            def _calendar_changed(event: Event[EventStateChangedData]) -> None:
                _refresh()

            self.config_entry.async_on_unload(
                async_track_state_change_event(self.hass, [self.calendar_id], _calendar_changed)
            )

    # ------------------------------------------------------------ update
    async def _async_update_data(self) -> ScheduleData:
        today = dt_util.now().date()
        last = today + timedelta(days=HORIZON_DAYS - 1)
        days = build_schedule(self.rules, today, HORIZON_DAYS)
        data = ScheduleData(today=today, days=days)

        if self.calendar_id:
            try:
                events = await self._async_get_exception_events(today, last)
            except Exception as err:  # noqa: BLE001
                if data.exceptions_ok:
                    _LOGGER.warning(
                        "Calendario eccezioni %s non leggibile (%s): uso solo le regole",
                        self.calendar_id,
                        err,
                    )
                data.exceptions_ok = False
                events = []
            all_types = list(self.rules)
            for start, end, summary in sorted(events, key=lambda e: e[0]):
                words = tokenize(summary)
                cancel = is_cancel(words)
                matched = self.matcher.match(summary)
                if not cancel and not matched:
                    _LOGGER.warning("Eccezione '%s' ignorata: nessun tipo di rifiuto riconosciuto", summary)
                    continue
                for day in event_days(start, end, today, last):
                    new = apply_exception(data.days.get(day, []), matched, cancel, all_types)
                    if new:
                        data.days[day] = new
                    else:
                        data.days.pop(day, None)
                    data.exceptions.setdefault(day, []).append(summary)

        data.days = {d: sort_codes(c) for d, c in data.days.items()}
        return data

    async def _async_get_exception_events(self, first: date, last: date):
        if self.hass.states.get(self.calendar_id) is None:
            raise RuntimeError("entità non trovata")
        response = await self.hass.services.async_call(
            CALENDAR_DOMAIN,
            "get_events",
            {
                "entity_id": self.calendar_id,
                "start_date_time": dt_util.start_of_local_day(first).isoformat(),
                "end_date_time": dt_util.start_of_local_day(last + timedelta(days=1)).isoformat(),
            },
            blocking=True,
            return_response=True,
        )
        out = []
        for raw in ((response or {}).get(self.calendar_id) or {}).get("events") or []:
            summary = (raw.get("summary") or "").strip()
            start, _ = parse_event_time(raw.get("start"))
            end, _ = parse_event_time(raw.get("end"))
            if summary and start is not None:
                out.append((start, end, summary))
        return out

    def schedule_for_range(self, first: date, last: date) -> dict[date, list[str]]:
        """Rules for any range (calendar view), with exceptions where known."""
        span = min((last - first).days + 1, 800)
        days = build_schedule(self.rules, first, max(span, 0))
        if self.data:
            for day in list(days) + list(self.data.days):
                if self.data.today <= day < self.data.today + timedelta(days=HORIZON_DAYS) and first <= day <= last:
                    if day in self.data.days:
                        days[day] = self.data.days[day]
                    else:
                        days.pop(day, None)
        return {d: sort_codes(c) for d, c in days.items()}

