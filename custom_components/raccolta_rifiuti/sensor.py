"""Sensor platform for Raccolta Rifiuti, fed by a Home Assistant calendar."""

# Creato da domoticafacile.it
from __future__ import annotations

from datetime import date, datetime, timedelta
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.calendar import DOMAIN as CALENDAR_DOMAIN
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA as SENSOR_PLATFORM_SCHEMA,
    SensorEntity,
)
from homeassistant.const import CONF_NAME, STATE_UNAVAILABLE
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_COLLECTION_TYPE_CODES,
    ATTR_COLLECTION_TYPES,
    ATTR_DAYS_REMAINING,
    ATTR_EVENT_START_TIME,
    ATTR_EVENT_SUMMARY,
    ATTR_NEXT_COLLECTION_DATE,
    ATTR_NEXT_COLLECTION_TYPE_CODES,
    ATTR_NEXT_COLLECTION_TYPES,
    CONF_CALENDAR,
    CONF_KEYWORDS,
    CONF_LANGUAGE,
    CONF_LANGUAGE_AUTO,
    CONF_LOOKAHEAD_DAYS,
    DEFAULT_LANGUAGE_OPTION,
    DEFAULT_LOOKAHEAD_DAYS,
    DOMAIN,
    IMAGE_BASE_PATH,
)
from .localization import (
    DEFAULT_IMAGE,
    LABELS,
    STRINGS,
    SUPPORTED_LANGUAGES,
    TYPE_IMAGES,
    TYPE_ORDER,
    TYPE_UNKNOWN,
    build_keyword_index,
    resolve_language,
)
from .parser import KeywordMatcher, event_days, parse_event_time

_LOGGER = logging.getLogger(__name__)

# Safety-net polling. The sensor is ALSO refreshed right after midnight and
# whenever the calendar entity changes state, so it no longer waits up to
# 30 minutes to notice the new day or a just-started event.
SCAN_INTERVAL = timedelta(minutes=30)

# Max lookahead: get_events over a very long window is pointless and slow.
MAX_LOOKAHEAD_DAYS = 60

_TYPE_RANK = {code: idx for idx, code in enumerate(TYPE_ORDER)}


def _type_codes(value: Any) -> list[str]:
    """Validate the value of a custom keyword: one code or a list of codes."""
    codes = value if isinstance(value, list) else [value]
    return [cv.slug(str(code).strip().lower()) for code in codes]


PLATFORM_SCHEMA = SENSOR_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_CALENDAR): cv.entity_domain(CALENDAR_DOMAIN),
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_LOOKAHEAD_DAYS, default=DEFAULT_LOOKAHEAD_DAYS): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=MAX_LOOKAHEAD_DAYS)
        ),
        vol.Optional(CONF_LANGUAGE, default=DEFAULT_LANGUAGE_OPTION): vol.In(
            (CONF_LANGUAGE_AUTO, *SUPPORTED_LANGUAGES)
        ),
        vol.Optional(CONF_KEYWORDS, default={}): {cv.string: _type_codes},
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Raccolta Rifiuti sensor platform.

    The entity is always created, even if the calendar is not loaded yet
    (CalDAV / Google / Local Calendar may come up after the sensor platform):
    it stays unavailable and refreshes itself as soon as the calendar appears.
    Previously the sensor was silently never created in that case.
    """
    keywords = build_keyword_index()
    for phrase, codes in config[CONF_KEYWORDS].items():
        keywords[phrase] = tuple(codes)

    async_add_entities(
        [
            RaccoltaRifiutiSensor(
                name=config.get(CONF_NAME),
                calendar_entity_id=config[CONF_CALENDAR],
                lookahead_days=config[CONF_LOOKAHEAD_DAYS],
                language=config[CONF_LANGUAGE],
                matcher=KeywordMatcher(keywords),
            )
        ],
        True,
    )


class RaccoltaRifiutiSensor(SensorEntity):
    """Today's waste collection(s) plus the next one within lookahead_days."""

    _attr_icon = "mdi:trash-can-outline"

    def __init__(
        self,
        name: str | None,
        calendar_entity_id: str,
        lookahead_days: int,
        language: str,
        matcher: KeywordMatcher,
    ) -> None:
        self._configured_name = name  # None => localized default name
        self._calendar_entity_id = calendar_entity_id
        self._lookahead_days = lookahead_days
        self._configured_language = language  # "auto", "it" or "en"
        self._matcher = matcher

        # Unchanged from previous versions: keeps the entity registry entry.
        self._attr_unique_id = f"{DOMAIN}_{calendar_entity_id}_next_collection"
        self._attr_available = False
        self._attr_native_value = None
        self._attr_extra_state_attributes = self._default_attributes()
        self._attr_entity_picture = f"{IMAGE_BASE_PATH}{DEFAULT_IMAGE}"
        self._last_problem: str | None = None

    # ------------------------------------------------------------------ HA hooks

    async def async_added_to_hass(self) -> None:
        """Refresh on calendar changes and right after midnight."""

        @callback
        def _calendar_changed(event: Event[EventStateChangedData]) -> None:
            new_state = event.data["new_state"]
            if new_state is None or new_state.state == STATE_UNAVAILABLE:
                return
            old_state = event.data["old_state"]
            # Skip pure attribute churn of an unchanged event.
            if (
                old_state is not None
                and old_state.state == new_state.state
                and old_state.attributes.get("message") == new_state.attributes.get("message")
                and old_state.attributes.get("start_time")
                == new_state.attributes.get("start_time")
                and self.available
            ):
                return
            self.async_schedule_update_ha_state(True)

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._calendar_entity_id], _calendar_changed
            )
        )

        @callback
        def _new_day(_now: datetime) -> None:
            self.async_schedule_update_ha_state(True)

        self.async_on_remove(
            async_track_time_change(self.hass, _new_day, hour=0, minute=0, second=5)
        )

    # ------------------------------------------------------------- localization

    def _language(self) -> str:
        if self._configured_language != CONF_LANGUAGE_AUTO:
            return self._configured_language
        return resolve_language(getattr(self.hass.config, "language", None))

    def _strings(self) -> dict[str, str]:
        return STRINGS[self._language()]

    @property
    def name(self) -> str:
        if self._configured_name:
            return self._configured_name
        if self.hass is None:  # before being added to HA
            return STRINGS["it"]["default_name"]
        return self._strings()["default_name"]

    # --------------------------------------------------------------- helpers

    @staticmethod
    def _default_attributes() -> dict[str, Any]:
        return {
            ATTR_EVENT_SUMMARY: None,
            ATTR_EVENT_START_TIME: None,
            ATTR_COLLECTION_TYPES: [],
            ATTR_COLLECTION_TYPE_CODES: [],
            ATTR_DAYS_REMAINING: None,
            ATTR_NEXT_COLLECTION_DATE: None,
            ATTR_NEXT_COLLECTION_TYPES: [],
            ATTR_NEXT_COLLECTION_TYPE_CODES: [],
            "description": None,
            "location": None,
        }

    def _label(self, code: str) -> str:
        labels = LABELS[self._language()]
        return labels.get(code) or code.replace("_", " ").capitalize()

    def _set_problem(self, key: str, message: str, *args: Any) -> None:
        """Mark the sensor unavailable, logging each distinct problem once."""
        if self._last_problem != key:
            _LOGGER.warning(message, *args)
            self._last_problem = key
        self._attr_available = False
        self._attr_native_value = None
        self._attr_extra_state_attributes = self._default_attributes()
        self._attr_entity_picture = f"{IMAGE_BASE_PATH}{DEFAULT_IMAGE}"

    def _analyze_day(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        """Recognize the waste types of the events of a single day."""
        codes: set[str] = set()
        summaries: list[str] = []
        for event in events:
            summary = event["summary"]
            summaries.append(summary)
            found = self._matcher.match(summary)
            if not found:
                _LOGGER.warning(
                    "Nessun tipo di rifiuto riconosciuto in '%s' (puoi aggiungerlo "
                    "con l'opzione 'keywords')",
                    summary,
                )
                found = [TYPE_UNKNOWN]
            codes.update(found)

        ordered = sorted(
            codes,
            key=lambda c: (c == TYPE_UNKNOWN, _TYPE_RANK.get(c, len(_TYPE_RANK)), c),
        )
        first = events[0]
        return {
            "codes": ordered,
            "labels": [self._label(code) for code in ordered],
            "image": next(
                (TYPE_IMAGES[c] for c in ordered if c in TYPE_IMAGES), DEFAULT_IMAGE
            ),
            "summaries": summaries,
            "start": first["start"].isoformat(),
            "description": first.get("description"),
            "location": first.get("location"),
        }

    async def _async_fetch_events(self, start: datetime, end: datetime) -> list[dict]:
        response = await self.hass.services.async_call(
            CALENDAR_DOMAIN,
            "get_events",
            {
                "entity_id": self._calendar_entity_id,
                "start_date_time": start.isoformat(),
                "end_date_time": end.isoformat(),
            },
            blocking=True,
            return_response=True,
        )
        entity_response = (response or {}).get(self._calendar_entity_id) or {}
        return list(entity_response.get("events") or [])

    # ---------------------------------------------------------------- update

    async def async_update(self) -> None:
        """Read today .. today+lookahead_days from the calendar in one call."""
        if self.hass.states.get(self._calendar_entity_id) is None:
            self._set_problem(
                "missing",
                "Calendario %s non (ancora) disponibile: il sensore resterà "
                "'non disponibile' finché il calendario non viene caricato",
                self._calendar_entity_id,
            )
            return

        today = dt_util.now().date()
        last_day = today + timedelta(days=self._lookahead_days)
        window_start = dt_util.start_of_local_day(today)
        window_end = dt_util.start_of_local_day(last_day + timedelta(days=1))

        try:
            raw_events = await self._async_fetch_events(window_start, window_end)
        except Exception as err:  # noqa: BLE001 - any calendar backend error
            self._set_problem(
                "service",
                "Errore leggendo gli eventi di %s: %s",
                self._calendar_entity_id,
                err,
            )
            return

        if self._last_problem is not None:
            _LOGGER.info("Calendario %s di nuovo disponibile", self._calendar_entity_id)
        self._last_problem = None
        self._attr_available = True

        events_by_day: dict[date, list[dict[str, Any]]] = {}
        for raw in raw_events:
            summary = (raw.get("summary") or raw.get("title") or "").strip()
            if not summary:
                continue
            start, _all_day = parse_event_time(raw.get("start"))
            if start is None:
                _LOGGER.debug("Evento senza data di inizio valida, ignorato: %s", raw)
                continue
            end, _ = parse_event_time(raw.get("end"))
            event = {
                "summary": summary,
                "start": start,
                "description": raw.get("description"),
                "location": raw.get("location"),
            }
            for day in event_days(start, end, today, last_day):
                events_by_day.setdefault(day, []).append(event)

        for day_events in events_by_day.values():
            day_events.sort(key=lambda ev: ev["start"])

        attributes = self._default_attributes()
        picture = DEFAULT_IMAGE

        today_events = events_by_day.get(today)
        if today_events:
            info = self._analyze_day(today_events)
            state = ", ".join(info["labels"])
            attributes.update(
                {
                    ATTR_EVENT_SUMMARY: ", ".join(info["summaries"])[:1024],
                    ATTR_EVENT_START_TIME: info["start"],
                    ATTR_COLLECTION_TYPES: info["labels"],
                    ATTR_COLLECTION_TYPE_CODES: info["codes"],
                    "description": info["description"],
                    "location": info["location"],
                }
            )
            picture = info["image"]
        else:
            state = self._strings()["no_event"]

        # Next collection: today if there is one, otherwise the first day
        # with events within lookahead_days.
        for offset in range(self._lookahead_days + 1):
            day = today + timedelta(days=offset)
            if day_events := events_by_day.get(day):
                info = self._analyze_day(day_events)
                attributes.update(
                    {
                        ATTR_DAYS_REMAINING: offset,
                        ATTR_NEXT_COLLECTION_DATE: day.isoformat(),
                        ATTR_NEXT_COLLECTION_TYPES: info["labels"],
                        ATTR_NEXT_COLLECTION_TYPE_CODES: info["codes"],
                    }
                )
                break

        self._attr_native_value = state if len(state) <= 255 else state[:252] + "..."
        self._attr_extra_state_attributes = attributes
        self._attr_entity_picture = f"{IMAGE_BASE_PATH}{picture}"
