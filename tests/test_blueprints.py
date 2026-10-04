"""Blueprints: valid schema + automation config valid once instantiated."""
import pathlib

import pytest
from homeassistant.components.blueprint import models
from homeassistant.components.automation.config import (
    AUTOMATION_BLUEPRINT_SCHEMA,
    async_validate_config_item,
)
from homeassistant.util.yaml import load_yaml

BP_DIR = pathlib.Path(__file__).resolve().parents[1] / "blueprints/automation/raccolta_rifiuti"

INPUTS = {
    "toggle_entity": "input_boolean.x",
    "target_automation": "automation.y",
    "sensore_raccolta": "sensor.raccolta_rifiuti",
    "dispositivo_alexa": "media_player.echo",
    "dispositivo_google": "media_player.nest",
    "motore_tts": "tts.google_translate_it_com",
    "azioni_notifica": [{"action": "notify.mobile_app_tel", "data": {"message": "{{ messaggio }}"}}],
}


@pytest.mark.parametrize("path", sorted(BP_DIR.glob("*.yaml")), ids=lambda p: p.name)
async def test_blueprint(hass, path):
    bp = models.Blueprint(load_yaml(path), expected_domain="automation", schema=AUTOMATION_BLUEPRINT_SCHEMA)
    needed = {k: INPUTS[k] for k in bp.inputs if k in INPUTS}
    inst = models.BlueprintInputs(bp, {"use_blueprint": {"path": path.name, "input": needed}})
    inst.validate()
    conf = inst.async_substitute()
    conf["id"] = "t"
    res = await async_validate_config_item(hass, "automation.t", conf)
    assert res is not None and res.validation_error is None, res.validation_error


async def test_example_automation(hass):
    path = BP_DIR.parents[2] / "examples/automazione_notifica_vale.yaml"
    conf = load_yaml(path)
    conf["id"] = "x"
    res = await async_validate_config_item(hass, "automation.x", conf)
    assert res.validation_error is None, res.validation_error
