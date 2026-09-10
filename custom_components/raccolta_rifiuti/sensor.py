# -*- coding: utf-8 -*-
"""Sensor platform for Raccolta Rifiuti using calendar event fetching via service call."""

# Creato da domoticafacile.it
import logging
import re
from datetime import timedelta, date, datetime

import voluptuous as vol
from homeassistant.components.calendar import DOMAIN as CALENDAR_DOMAIN
from homeassistant.const import CONF_NAME, EVENT_HOMEASSISTANT_START
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
import homeassistant.helpers.config_validation as cv
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_CALENDAR,
    CONF_LOOKAHEAD_DAYS,
    CONF_LANGUAGE,
    CONF_LANGUAGE_AUTO,
    DEFAULT_LOOKAHEAD_DAYS,
    DEFAULT_LANGUAGE_OPTION,
    IMAGE_BASE_PATH,
    ATTR_EVENT_SUMMARY,
    ATTR_EVENT_START_TIME,
    ATTR_DAYS_REMAINING,
    ATTR_COLLECTION_TYPES,
    ATTR_COLLECTION_TYPE_CODES,
    ATTR_NEXT_COLLECTION_DATE,
    ATTR_NEXT_COLLECTION_TYPES,
    ATTR_NEXT_COLLECTION_TYPE_CODES,
)
from .localization import (
    TYPE_IMAGES,
    DEFAULT_IMAGE,
    LABELS,
    STRINGS,
    TYPE_UNKNOWN,
    SUPPORTED_LANGUAGES,
    resolve_language,
    build_keyword_index,
)

_LOGGER = logging.getLogger(__name__)

# The sensor's state realistically only changes once a day (when the
# calendar entry for the next collection is added, the evening before).
# Polling every few seconds (the historical default) needlessly calls
# calendar.get_events very often; 30 minutes keeps the sensor responsive
# after a restart or a new calendar entry without hammering the calendar
# integration. Still overridable per-entry with `scan_interval:` in YAML.
SCAN_INTERVAL = timedelta(minutes=30)

# Built once at import time: merges keywords from every supported source
# language, sorted longest-first so multi-word phrases are tried before
# their shorter substrings (e.g. "rifiuto secco" before "secco").
KEYWORD_INDEX = build_keyword_index()
SORTED_KEYWORDS = sorted(KEYWORD_INDEX.keys(), key=len, reverse=True)

# Punctuation/conjunctions that may separate multiple waste types written in
# a single calendar event summary (e.g. "Carta, Vetro" or "Carta e Vetro").
_SEPARATOR_RE = re.compile(r"[,;/+&]")
_CONJUNCTION_RE = re.compile(r"\b(e|and)\b")
_WHITESPACE_RE = re.compile(r"\s+")

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_CALENDAR): cv.entity_id,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_LOOKAHEAD_DAYS, default=DEFAULT_LOOKAHEAD_DAYS): cv.positive_int,
        vol.Optional(CONF_LANGUAGE, default=DEFAULT_LANGUAGE_OPTION): vol.In(
            (CONF_LANGUAGE_AUTO,) + SUPPORTED_LANGUAGES
        ),
    }
)

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Raccolta Rifiuti sensor platform."""
    calendar_entity_id = config[CONF_CALENDAR]
    sensor_name = config.get(CONF_NAME)  # None => use localized default name
    lookahead_days = config[CONF_LOOKAHEAD_DAYS]
    language = config[CONF_LANGUAGE]

    _LOGGER.debug("Setting up Raccolta Rifiuti sensor for calendar: %s", calendar_entity_id)

    async def _async_finalize_setup(_event=None) -> None:
        """Finalize setup after calendar entity might be ready."""
        _LOGGER.debug("Attempting to finalize Raccolta Rifiuti sensor setup.")
        if hass.states.get(calendar_entity_id) is None:
            _LOGGER.error(
                "Calendar entity %s STILL not found after Home Assistant start. "
                "Please check your configuration and calendar integration.",
                calendar_entity_id,
            )
            return

        _LOGGER.info("Calendar entity %s found. Adding Raccolta Rifiuti sensor.", calendar_entity_id)
        sensor = RaccoltaRifiutiSensor(hass, sensor_name, calendar_entity_id, lookahead_days, language)
        async_add_entities([sensor], True)

    if hass.states.get(calendar_entity_id) is not None:
        _LOGGER.debug("Calendar entity %s found immediately.", calendar_entity_id)
        await _async_finalize_setup()
    else:
        # Normale durante l'avvio: la piattaforma sensor viene spesso
        # inizializzata prima che l'entità calendario sia pronta. Non è un
        # errore: viene ritentato automaticamente a EVENT_HOMEASSISTANT_START.
        _LOGGER.info(
            "Calendar entity %s not found immediately (normale in fase di avvio). "
            "Will attempt setup again after Home Assistant starts.",
            calendar_entity_id,
        )
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, _async_finalize_setup)


class RaccoltaRifiutiSensor(SensorEntity):
    """Representation of a Raccolta Rifiuti Sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str | None,
        calendar_entity_id: str,
        lookahead_days: int,
        language: str,
    ):
        """Initialize the sensor."""
        self.hass = hass
        self._configured_name = name  # None => derive from display language
        self._calendar_entity_id = calendar_entity_id
        self._lookahead_days = lookahead_days
        self._configured_language = language  # "auto", "it" or "en"

        self._attr_unique_id = f"{DOMAIN}_{calendar_entity_id}_next_collection"
        self._attr_icon = "mdi:trash-can-outline"

        self._state = self._strings()["no_event"]
        self._attributes = self._default_attributes()
        self._entity_picture_path = f"{IMAGE_BASE_PATH}{DEFAULT_IMAGE}"

    def _language(self) -> str:
        """Return the display language actually in effect.

        "auto" follows Home Assistant's configured language live (it is
        re-evaluated on every access, so changing HA's language updates the
        sensor's texts on the next update without restarting it).
        """
        if self._configured_language != CONF_LANGUAGE_AUTO:
            return self._configured_language
        return resolve_language(getattr(self.hass.config, "language", None))

    def _strings(self) -> dict:
        return STRINGS[self._language()]

    def _labels(self) -> dict:
        return LABELS[self._language()]

    def _default_attributes(self) -> dict:
        """Return default attributes."""
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

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        if self._configured_name:
            return self._configured_name
        return self._strings()["default_name"]

    @property
    def state(self) -> str:
        """Return the state of the sensor (tipi di raccolta di OGGI, combinati)."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        return self._attributes

    @property
    def entity_picture(self) -> str | None:
        """Return the entity picture."""
        return self._entity_picture_path

    @staticmethod
    def _normalize_summary(event_summary: str) -> str:
        """Normalize a (already lowercased) summary for keyword matching.

        Replaces separators such as commas, slashes and "and"/"e" with
        spaces, so that a single calendar event listing several waste
        types (e.g. "Carta, Vetro" or "Carta e Vetro") has every type
        recognized, not just the last one.
        """
        normalized = _SEPARATOR_RE.sub(" ", event_summary)
        normalized = _CONJUNCTION_RE.sub(" ", normalized)
        normalized = _WHITESPACE_RE.sub(" ", normalized).strip()
        return normalized

    def _analyze_day_events(self, day_events: list) -> dict:
        """Match a single day's calendar events against known waste-type keywords.

        Shared between "today" and the look-ahead search below, so both use
        exactly the same recognition logic.
        """
        labels = self._labels()

        found_codes = set()
        found_images = set()
        event_summaries = []
        first_event_start_iso = None
        first_event_description = None
        first_event_location = None

        for idx, event in enumerate(day_events):
            raw_summary = event.get('summary', '')
            event_summary = raw_summary.lower().strip()
            if not event_summary:
                _LOGGER.debug("Skipping event with empty summary: %s", event)
                continue

            event_summaries.append(raw_summary)

            if idx == 0:
                try:
                    first_event_start_iso = event['start'].isoformat()
                    first_event_description = event.get('description')
                    first_event_location = event.get('location')
                except Exception as e:
                    _LOGGER.warning("Could not format start time or get details for first event: %s", e)

            matched_this_event = False
            normalized_summary = self._normalize_summary(event_summary)
            summary_for_check = f" {normalized_summary} "

            for keyword in SORTED_KEYWORDS:
                if f" {keyword} " in summary_for_check or \
                    normalized_summary.startswith(keyword + " ") or \
                    normalized_summary.endswith(" " + keyword) or \
                    normalized_summary == keyword:

                    canonical_type = KEYWORD_INDEX[keyword]
                    image_file = TYPE_IMAGES.get(canonical_type, DEFAULT_IMAGE)

                    _LOGGER.debug("Keyword '%s' matched in summary '%s'. Type: %s, Image: %s",
                                  keyword, raw_summary, canonical_type, image_file)
                    found_codes.add(canonical_type)
                    found_images.add(image_file)
                    matched_this_event = True
                    # Keep scanning: a single event may list more than one type.
                    summary_for_check = summary_for_check.replace(f" {keyword} ", "  ", 1)

            if not matched_this_event:
                _LOGGER.warning("No keyword matched for event summary: '%s'. Adding as unknown.", raw_summary)
                found_codes.add(TYPE_UNKNOWN)

        sorted_codes = sorted(c for c in found_codes if c != TYPE_UNKNOWN)
        if TYPE_UNKNOWN in found_codes:
            sorted_codes.append(TYPE_UNKNOWN)

        sorted_labels = [labels.get(code, code.capitalize()) for code in sorted_codes]

        return {
            "codes": sorted_codes,
            "labels": sorted_labels,
            "images": sorted(found_images),
            "event_summaries": event_summaries,
            "first_event_start_iso": first_event_start_iso,
            "first_event_description": first_event_description,
            "first_event_location": first_event_location,
        }

    async def async_update(self) -> None:
        """Fetch new state data using the calendar.get_events service.

        Fetches one combined window from today through
        today + lookahead_days (inclusive) in a single service call, so
        `lookahead_days` is now actually used: if nothing is scheduled
        today, the sensor looks ahead and reports the next collection it
        finds within that window via days_remaining/next_collection_*.
        `state`/`collection_types` keep describing strictly TODAY, so
        existing automations relying on them are unaffected.
        """
        _LOGGER.debug("Updating Raccolta Rifiuti sensor by calling calendar.get_events for %s", self._calendar_entity_id)

        strings = self._strings()

        calendar_entity_state = self.hass.states.get(self._calendar_entity_id)
        if calendar_entity_state is None:
            _LOGGER.warning("Calendar entity %s not found during update.", self._calendar_entity_id)
            self._state = strings["calendar_not_found"]
            self._attributes = self._default_attributes()
            self._entity_picture_path = f"{IMAGE_BASE_PATH}{DEFAULT_IMAGE}"
            return

        today = dt_util.now().date()
        start_date = dt_util.start_of_local_day()  # Inizia da mezzanotte locale (oggi)
        # Copre l'intera finestra di lookahead in un'unica chiamata al servizio.
        end_date = dt_util.start_of_local_day(
            start_date + timedelta(days=self._lookahead_days + 1)
        ) - timedelta(seconds=1)
        _LOGGER.debug("Fetching events between %s and %s", start_date.isoformat(), end_date.isoformat())

        try:
            service_data = {
                "entity_id": self._calendar_entity_id,
                "start_date_time": start_date.isoformat(),
                "end_date_time": end_date.isoformat(),
            }

            response = await self.hass.services.async_call(
                CALENDAR_DOMAIN,
                "get_events",
                service_data,
                blocking=True,
                return_response=True,
            )

            calendar_events = []
            if response and self._calendar_entity_id in response:
                calendar_events_response = response[self._calendar_entity_id]
                if isinstance(calendar_events_response, dict) and "events" in calendar_events_response:
                    calendar_events = calendar_events_response["events"]
                elif isinstance(calendar_events_response, list):
                    calendar_events = calendar_events_response
                else:
                    _LOGGER.debug("Response format for %s doesn't contain a list or 'events' dict: %s", self._calendar_entity_id, response)
            elif isinstance(response, dict) and "events" in response:
                calendar_events = response["events"]
            else:
                _LOGGER.debug("No events found or unexpected response structure from calendar.get_events for %s: %s", self._calendar_entity_id, response)

        except Exception as e:
            _LOGGER.error(
                "Error calling calendar.get_events service for %s: %s",
                self._calendar_entity_id, e, exc_info=True
            )
            self._state = strings["service_error"]
            self._attributes = self._default_attributes()
            self._entity_picture_path = f"{IMAGE_BASE_PATH}{DEFAULT_IMAGE}"
            return

        _LOGGER.debug("Found %d raw events for %s via service call", len(calendar_events), self._calendar_entity_id)

        events_by_date: dict = {}
        max_date = today + timedelta(days=self._lookahead_days)

        for event in calendar_events:
            try:
                start_val = event.get('start')
                event_start_dt = None

                if isinstance(start_val, str):
                    if 'T' in start_val:
                        parsed_dt = dt_util.parse_datetime(start_val)
                        if parsed_dt:
                            event_start_dt = dt_util.as_local(parsed_dt)
                    else:
                        parsed_date = dt_util.parse_date(start_val)
                        if parsed_date:
                            event_start_dt = dt_util.start_of_local_day(parsed_date)
                elif isinstance(start_val, datetime):
                    event_start_dt = dt_util.as_local(start_val)
                elif isinstance(start_val, date):
                    event_start_dt = dt_util.start_of_local_day(start_val)

                if event_start_dt is None:
                    _LOGGER.warning("Could not parse start time for event, skipping: %s", event)
                    continue

                event_date = event_start_dt.date()
                if event_date < today or event_date > max_date:
                    continue

                processed_event = {
                    'summary': event.get('summary') or event.get('title', ''),
                    'start': event_start_dt,
                    'end': event.get('end'),
                    'location': event.get('location'),
                    'description': event.get('description'),
                }
                events_by_date.setdefault(event_date, []).append(processed_event)
                _LOGGER.debug("Adding event '%s' on %s to process list", processed_event['summary'], event_date)

            except (KeyError, TypeError, ValueError) as e:
                _LOGGER.warning("Could not process event data, skipping. Error: %s, Event: %s", e, event)
                continue

        today_events = events_by_date.get(today, [])

        if today_events:
            info = self._analyze_day_events(today_events)

            state_text = ", ".join(info["labels"])
            if len(state_text) > 255:
                state_text = state_text[:252] + "..."
            self._state = state_text

            self._attributes = {
                ATTR_EVENT_SUMMARY: ", ".join(info["event_summaries"])[:1024],
                ATTR_EVENT_START_TIME: info["first_event_start_iso"],
                ATTR_COLLECTION_TYPES: info["labels"],
                ATTR_COLLECTION_TYPE_CODES: info["codes"],
                ATTR_DAYS_REMAINING: 0,
                ATTR_NEXT_COLLECTION_DATE: today.isoformat(),
                ATTR_NEXT_COLLECTION_TYPES: info["labels"],
                ATTR_NEXT_COLLECTION_TYPE_CODES: info["codes"],
                "description": info["first_event_description"],
                "location": info["first_event_location"],
            }

            if info["images"]:
                self._entity_picture_path = f"{IMAGE_BASE_PATH}{info['images'][0]}"
            else:
                self._entity_picture_path = f"{IMAGE_BASE_PATH}{DEFAULT_IMAGE}"

            _LOGGER.debug("Sensor updated for today: state=%s attrs=%s", self._state, self._attributes)
            return

        # Nessun evento oggi: usa lookahead_days per cercare la prossima
        # raccolta utile, così l'opzione (prima inutilizzata) ha un effetto.
        self._state = strings["no_event"]
        self._attributes = self._default_attributes()
        self._entity_picture_path = f"{IMAGE_BASE_PATH}{DEFAULT_IMAGE}"

        for day_offset in range(1, self._lookahead_days + 1):
            target_date = today + timedelta(days=day_offset)
            day_events = events_by_date.get(target_date)
            if not day_events:
                continue

            info = self._analyze_day_events(day_events)
            self._attributes[ATTR_DAYS_REMAINING] = day_offset
            self._attributes[ATTR_NEXT_COLLECTION_DATE] = target_date.isoformat()
            self._attributes[ATTR_NEXT_COLLECTION_TYPES] = info["labels"]
            self._attributes[ATTR_NEXT_COLLECTION_TYPE_CODES] = info["codes"]
            _LOGGER.debug(
                "No collection today; next one found in %d day(s) on %s: %s",
                day_offset, target_date, info["labels"],
            )
            break

        _LOGGER.debug("Sensor updated (no event today): state=%s attrs=%s", self._state, self._attributes)
