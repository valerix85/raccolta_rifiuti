"""UI mode: config flow, sensors, exceptions, calendar, text entities."""
from __future__ import annotations

import datetime as dt

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.raccolta_rifiuti.const import CONF_EXCEPTIONS_CALENDAR, CONF_RULES, DOMAIN

from .helpers import async_setup_fake_calendar

VALE = {
    "residual": "ven",
    "organic": "lun,ven",
    "paper": "lun",
    "plastic": "mer",
    "glass": "mer",
    "green": "mer",
    "metal": "",
}
P = "raccolta_differenziata"


@pytest.fixture
async def setup_tz(hass, freezer):
    await hass.config.async_set_time_zone("Europe/Rome")
    hass.config.language = "it"
    freezer.move_to("2026-10-04 18:00:00+02:00")  # domenica


async def _entry(hass, rules=VALE, calendar=None):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Raccolta Differenziata",
        unique_id=P,
        data={},
        options={CONF_RULES: dict(rules), CONF_EXCEPTIONS_CALENDAR: calendar},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_config_flow(hass, setup_tz):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"name": "Casa"})
    assert result["step_id"] == "rules"
    bad = await hass.config_entries.flow.async_configure(result["flow_id"], {"paper": "lunedx"})
    assert bad["errors"] == {"paper": "invalid_rule"}
    assert "lunedx" in bad["description_placeholders"]["error"]
    empty = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert empty["errors"] == {"base": "no_rules"}
    ok = await hass.config_entries.flow.async_configure(result["flow_id"], {"paper": "lun", "organic": "lun,ven"})
    assert ok["type"] is FlowResultType.CREATE_ENTRY
    assert ok["title"] == "Casa"
    await hass.async_block_till_done()
    assert hass.states.get("sensor.casa_domani").state == "Umido, Carta"


async def test_vale_schedule(hass, setup_tz):
    await _entry(hass)
    tomorrow = hass.states.get(f"sensor.{P}_domani")
    assert tomorrow.state == "Umido, Carta"
    assert tomorrow.attributes["collection_types"] == ["Umido", "Carta"]
    assert tomorrow.attributes["message"] == "Umido e Carta"
    assert tomorrow.attributes["entity_picture"].endswith("umido.png")
    assert hass.states.get(f"sensor.{P}_oggi").state == "Nessuna raccolta programmata"
    nxt = hass.states.get(f"sensor.{P}_prossima_raccolta")
    assert nxt.state == "2026-10-05" and nxt.attributes["days_remaining"] == 1
    secco = hass.states.get(f"sensor.{P}_secco_indifferenziata")
    assert secco.state == "5"
    assert secco.attributes["upcoming"][:2] == ["2026-10-09", "2026-10-16"]
    assert hass.states.get(f"sensor.{P}_metallo") is None  # no rule => no sensor
    assert hass.states.get(f"text.{P}_giorni_umido").state == "lun,ven"


async def test_midnight(hass, setup_tz, freezer):
    await _entry(hass)
    freezer.move_to("2026-10-05 00:00:06+02:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(f"sensor.{P}_oggi").state == "Umido, Carta"
    assert hass.states.get(f"sensor.{P}_domani").state == "Nessuna raccolta programmata"


async def test_exceptions(hass, setup_tz):
    cal = await async_setup_fake_calendar(hass)
    tz = dt_util.get_default_time_zone()

    def allday(d, summary):
        cal.add(summary, dt.datetime.combine(d, dt.time(0), tz), dt.datetime.combine(d + dt.timedelta(1), dt.time(0), tz))

    allday(dt.date(2026, 10, 5), "No umido")  # lunedì: resta solo carta
    allday(dt.date(2026, 10, 7), "Raccolta sospesa (sciopero)")  # mercoledì: niente
    allday(dt.date(2026, 10, 8), "Recupero plastica e vetro")  # giovedì: aggiunta
    await _entry(hass, calendar="calendar.raccolta_rifiuti")
    assert hass.states.get(f"sensor.{P}_domani").state == "Carta"
    assert hass.states.get(f"sensor.{P}_domani").attributes["exceptions"] == ["No umido"]
    plastica = hass.states.get(f"sensor.{P}_plastica")
    assert plastica.attributes["upcoming"][0] == "2026-10-08"
    verde = hass.states.get(f"sensor.{P}_verde")
    assert verde.attributes["upcoming"][0] == "2026-10-14"


async def test_text_entity_updates_rules(hass, setup_tz):
    entry = await _entry(hass)
    await hass.services.async_call(
        "text", "set_value", {"entity_id": f"text.{P}_giorni_carta", "value": "mar"}, blocking=True
    )
    await hass.async_block_till_done()
    assert entry.options[CONF_RULES]["paper"] == "mar"
    assert hass.states.get(f"sensor.{P}_domani").state == "Umido"
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "text", "set_value", {"entity_id": f"text.{P}_giorni_carta", "value": "boh"}, blocking=True
        )
    # enabling a new type reloads and creates its sensor
    await hass.services.async_call(
        "text", "set_value", {"entity_id": f"text.{P}_giorni_metallo", "value": "gio"}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(f"sensor.{P}_metallo").state == "4"


async def test_calendar_entity(hass, setup_tz):
    await _entry(hass)
    resp = await hass.services.async_call(
        "calendar",
        "get_events",
        {"entity_id": f"calendar.{P}", "start_date_time": "2026-10-05T00:00:00+02:00", "end_date_time": "2026-10-12T00:00:00+02:00"},
        blocking=True,
        return_response=True,
    )
    events = resp[f"calendar.{P}"]["events"]
    assert [(e["start"], e["summary"]) for e in events] == [
        ("2026-10-05", "Umido, Carta"),
        ("2026-10-07", "Plastica, Vetro, Verde"),
        ("2026-10-09", "Indifferenziata, Umido"),
    ]


async def test_options_flow(hass, setup_tz):
    entry = await _entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {**VALE, "paper": "sab"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert hass.states.get(f"sensor.{P}_carta").state == "6"


async def test_unload(hass, setup_tz):
    entry = await _entry(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
