# Creato da domoticafacile.it
"""Calendar entity showing the computed collections (UI mode)."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import RaccoltaCoordinator
from .entity import RaccoltaEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([RaccoltaCalendar(entry.runtime_data)])


class RaccoltaCalendar(RaccoltaEntity, CalendarEntity):
    """One all-day event per collection day, e.g. "Carta, Umido"."""

    _attr_translation_key = "collections"
    _attr_name = None  # the device name ("Raccolta Differenziata")

    def __init__(self, coordinator: RaccoltaCoordinator) -> None:
        super().__init__(coordinator, "calendar")

    def _event(self, day: date, codes: list[str]) -> CalendarEvent:
        data = self.coordinator.data
        description = None
        if data and data.exceptions.get(day):
            description = "Eccezioni: " + "; ".join(data.exceptions[day])
        return CalendarEvent(
            start=day,
            end=day + timedelta(days=1),
            summary=", ".join(self.labels(codes)),
            description=description,
            uid=f"{self.coordinator.config_entry.entry_id}-{day.isoformat()}",
        )

    @property
    def event(self) -> CalendarEvent | None:
        data = self.coordinator.data
        day, codes = data.next_collection(data.today)
        return self._event(day, codes) if day else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        first = dt_util.as_local(start_date).date()
        last = (dt_util.as_local(end_date) - timedelta(microseconds=1)).date()
        days = self.coordinator.schedule_for_range(first, last)
        return [self._event(day, codes) for day, codes in sorted(days.items())]
