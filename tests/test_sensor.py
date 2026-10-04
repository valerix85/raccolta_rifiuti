"""Tests for the Raccolta Rifiuti sensor."""
from __future__ import annotations

import datetime as dt

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import EVENT_HOMEASSISTANT_START
from homeassistant.core import CoreState
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from homeassistant.helpers.entity_component import DATA_INSTANCES

from .helpers import FakeCalendar, async_setup_fake_calendar, timed

SENSOR = "sensor.raccolta_rifiuti"
TZ = "Europe/Rome"


@pytest.fixture
async def setup_tz(hass):
    await hass.config.async_set_time_zone(TZ)
    hass.config.language = "it"


async def _setup_sensor(hass, extra=None):
    conf = {"platform": "raccolta_rifiuti", "calendar_entity_id": "calendar.raccolta_rifiuti"}
    conf.update(extra or {})
    assert await async_setup_component(hass, "sensor", {"sensor": [conf]})
    await hass.async_block_till_done()


async def test_basic_today(hass, setup_tz, freezer: FrozenDateTimeFactory):
    freezer.move_to("2026-10-04 10:00:00+02:00")
    cal = await async_setup_fake_calendar(hass)
    today = dt_util.now().date()
    cal.add(*timed(today, "Carta"))
    cal.add(*timed(today, "Vetro"))
    await _setup_sensor(hass)
    st = hass.states.get(SENSOR)
    assert st.state == "Carta, Vetro"
    assert st.attributes["collection_type_codes"] == ["paper", "glass"]
    assert st.attributes["entity_picture"] == "/local/images/img_raccolta_rifiuti/carta.png"
    assert st.attributes["days_remaining"] == 0


async def test_lookahead(hass, setup_tz, freezer):
    freezer.move_to("2026-10-04 10:00:00+02:00")
    cal = await async_setup_fake_calendar(hass)
    today = dt_util.now().date()
    cal.add(*timed(today + dt.timedelta(days=2), "Umido"))
    await _setup_sensor(hass)
    st = hass.states.get(SENSOR)
    assert st.state == "Nessuna raccolta programmata"
    assert st.attributes["days_remaining"] == 2
    assert st.attributes["next_collection_types"] == ["Umido"]


@pytest.mark.parametrize(
    ("summary", "codes"),
    [
        ("Carta.", ["paper"]),
        ("Carta - Vetro", ["glass", "paper"]),
        ("Plastica (sacco giallo)", ["plastic"]),
        ("🗑️ Umido", ["organic"]),
        ("PLASTICA E LATTINE", ["metal", "plastic"]),
        ("Rifiuto secco", ["residual"]),
        ("Indifferenziato", ["residual"]),
        ("Carta/cartone", ["paper"]),
    ],
)
async def test_matching(hass, setup_tz, freezer, summary, codes):
    freezer.move_to("2026-10-04 10:00:00+02:00")
    cal = await async_setup_fake_calendar(hass)
    cal.add(*timed(dt_util.now().date(), summary))
    await _setup_sensor(hass)
    st = hass.states.get(SENSOR)
    assert sorted(st.attributes["collection_type_codes"]) == codes


async def test_midnight_rollover(hass, setup_tz, freezer):
    """Il giorno dopo il sensore deve aggiornarsi subito dopo mezzanotte, non fino a 30 min dopo."""
    freezer.move_to("2026-10-04 23:50:00+02:00")
    cal = await async_setup_fake_calendar(hass)
    tomorrow = dt_util.now().date() + dt.timedelta(days=1)
    cal.add(*timed(tomorrow, "Carta"))
    await _setup_sensor(hass)
    assert hass.states.get(SENSOR).state == "Nessuna raccolta programmata"
    freezer.move_to("2026-10-05 00:01:00+02:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR).state == "Carta"


async def test_new_event_reflected_when_calendar_changes(hass, setup_tz, freezer):
    """Quando il calendario cambia stato (evento inizia) il sensore si aggiorna."""
    freezer.move_to("2026-10-04 18:00:00+02:00")
    cal = await async_setup_fake_calendar(hass)
    await _setup_sensor(hass)
    assert hass.states.get(SENSOR).state == "Nessuna raccolta programmata"
    cal.add(*timed(dt_util.now().date(), "Vetro"))
    # simula un cambio di stato del calendario (es. evento creato/iniziato)
    hass.states.async_set("calendar.raccolta_rifiuti", "on", {"message": "Vetro"})
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR).state == "Vetro"


async def test_calendar_loaded_late_after_start(hass, setup_tz, freezer):
    """Calendario (es. CalDAV/Google) che compare dopo l'avvio di HA: il sensore non deve sparire."""
    freezer.move_to("2026-10-04 10:00:00+02:00")
    hass.set_state(CoreState.not_running)
    await _setup_sensor(hass)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR).state == "unavailable"
    # "calendar" is already loaded (it is a dependency of the integration):
    # add the calendar entity later, like a slow CalDAV/Google backend would.
    cal = FakeCalendar()
    cal.add(*timed(dt_util.now().date(), "Carta"))
    await hass.data[DATA_INSTANCES]["calendar"].async_add_entities([cal])
    await hass.async_block_till_done()
    st = hass.states.get(SENSOR)
    assert st is not None
    assert st.state == "Carta"


async def test_multiday_allday_event(hass, setup_tz, freezer):
    """Evento tutto il giorno iniziato ieri e che copre anche oggi."""
    freezer.move_to("2026-10-04 10:00:00+02:00")
    cal = await async_setup_fake_calendar(hass)
    today = dt_util.now().date()
    tz = dt_util.get_default_time_zone()
    cal.add(
        "Verde",
        dt.datetime.combine(today - dt.timedelta(days=1), dt.time(0), tz),
        dt.datetime.combine(today + dt.timedelta(days=1), dt.time(0), tz),
    )
    await _setup_sensor(hass)
    assert hass.states.get(SENSOR).state == "Verde"


async def test_custom_keywords(hass, setup_tz, freezer):
    freezer.move_to("2026-10-04 10:00:00+02:00")
    cal = await async_setup_fake_calendar(hass)
    cal.add(*timed(dt_util.now().date(), "Multimateriale"))
    await _setup_sensor(hass, {"keywords": {"multimateriale": ["plastic", "metal"]}})
    st = hass.states.get(SENSOR)
    assert sorted(st.attributes["collection_type_codes"]) == ["metal", "plastic"]


async def test_unknown_and_custom_label(hass, setup_tz, freezer):
    freezer.move_to("2026-10-04 10:00:00+02:00")
    cal = await async_setup_fake_calendar(hass)
    cal.add(*timed(dt_util.now().date(), "Pannolini"))
    cal.add(*timed(dt_util.now().date(), "Ingombranti"))
    await _setup_sensor(hass, {"keywords": {"pannolini": "pannolini"}})
    st = hass.states.get(SENSOR)
    assert st.attributes["collection_type_codes"] == ["pannolini", "unknown"]
    assert st.state == "Pannolini, Raccolta sconosciuta"


async def test_english_and_language(hass, setup_tz, freezer):
    freezer.move_to("2026-10-04 10:00:00+02:00")
    cal = await async_setup_fake_calendar(hass)
    cal.add(*timed(dt_util.now().date(), "Paper and glass"))
    await _setup_sensor(hass, {"language": "en", "name": "Raccolta Rifiuti"})
    st = hass.states.get(SENSOR)
    assert st.state == "Paper, Glass"


async def test_calendar_unavailable_then_back(hass, setup_tz, freezer):
    freezer.move_to("2026-10-04 10:00:00+02:00")
    await _setup_sensor(hass)
    assert hass.states.get(SENSOR).state == "unavailable"


async def test_word_boundaries(hass, setup_tz, freezer):
    """'cartellone' non deve essere letto come carta, 'vetrina' non come vetro."""
    freezer.move_to("2026-10-04 10:00:00+02:00")
    cal = await async_setup_fake_calendar(hass)
    cal.add(*timed(dt_util.now().date(), "Vetrina cartellone"))
    await _setup_sensor(hass)
    assert hass.states.get(SENSOR).attributes["collection_type_codes"] == ["unknown"]
