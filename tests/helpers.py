"""Fake calendar used by the tests."""
from __future__ import annotations

import datetime as dt

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockModule,
    MockPlatform,
    mock_integration,
    mock_platform,
)


class FakeCalendar(CalendarEntity):
    _attr_name = "Raccolta rifiuti"

    def __init__(self) -> None:
        self._attr_unique_id = "fake_raccolta"
        self.events: list[CalendarEvent] = []

    @property
    def event(self):
        now = dt_util.now()
        for ev in sorted(self.events, key=lambda e: e.start_datetime_local):
            if ev.start_datetime_local <= now < ev.end_datetime_local:
                return ev
        return None

    async def async_get_events(self, hass, start_date, end_date):
        return [
            e
            for e in self.events
            if e.start_datetime_local < end_date and e.end_datetime_local > start_date
        ]

    def add(self, summary, start, end):
        self.events.append(CalendarEvent(start=start, end=end, summary=summary))


def timed(day: dt.date, summary: str, h1=19, h2=23, m2=59):
    tz = dt_util.get_default_time_zone()
    return (
        summary,
        dt.datetime.combine(day, dt.time(h1, 0), tz),
        dt.datetime.combine(day, dt.time(h2, m2), tz),
    )


async def async_setup_fake_calendar(hass, add_now: bool = True) -> FakeCalendar:
    cal = FakeCalendar()

    async def _setup_platform(hass, config, async_add_entities, discovery_info=None):
        async_add_entities([cal])

    mock_integration(hass, MockModule("fakecal"))
    mock_platform(hass, "fakecal.calendar", MockPlatform(async_setup_platform=_setup_platform))
    if add_now:
        assert await async_setup_component(hass, "calendar", {"calendar": {"platform": "fakecal"}})
        await hass.async_block_till_done()
    return cal
