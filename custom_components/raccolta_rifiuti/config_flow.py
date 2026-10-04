# Creato da domoticafacile.it
"""UI configuration: name, weekly rules per waste type, exception calendar."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import slugify

from .const import CONF_EXCEPTIONS_CALENDAR, CONF_RULES, DEFAULT_ENTRY_NAME, DOMAIN
from .localization import TYPE_ORDER
from .schedule import validate_rule

CONF_NAME = "name"
_TEXT = selector.TextSelector(selector.TextSelectorConfig())
_CALENDAR = selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar"))


def _rules_schema(rules: dict[str, str], calendar: str | None) -> vol.Schema:
    fields: dict[Any, Any] = {}
    for code in TYPE_ORDER:
        fields[vol.Optional(code, description={"suggested_value": rules.get(code, "")})] = _TEXT
    fields[
        vol.Optional(CONF_EXCEPTIONS_CALENDAR, description={"suggested_value": calendar})
    ] = _CALENDAR
    return vol.Schema(fields)


def _validate(user_input: dict[str, Any]) -> tuple[dict[str, str], dict[str, str], str]:
    rules: dict[str, str] = {}
    errors: dict[str, str] = {}
    first_error = ""
    for code in TYPE_ORDER:
        value = (user_input.get(code) or "").strip()
        if error := validate_rule(value):
            errors[code] = "invalid_rule"
            first_error = first_error or error
        rules[code] = value
    if not errors and not any(rules.values()):
        errors["base"] = "no_rules"
    return rules, errors, first_error


class RaccoltaConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._name = DEFAULT_ENTRY_NAME

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._name = user_input[CONF_NAME].strip() or DEFAULT_ENTRY_NAME
            await self.async_set_unique_id(slugify(self._name))
            self._abort_if_unique_id_configured()
            return await self.async_step_rules()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_NAME, default=DEFAULT_ENTRY_NAME): _TEXT}),
        )

    async def async_step_rules(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        placeholders = {"error": ""}
        rules: dict[str, str] = {}
        calendar = None
        if user_input is not None:
            rules, errors, placeholders["error"] = _validate(user_input)
            calendar = user_input.get(CONF_EXCEPTIONS_CALENDAR)
            if not errors:
                return self.async_create_entry(
                    title=self._name,
                    data={},
                    options={CONF_RULES: rules, CONF_EXCEPTIONS_CALENDAR: calendar},
                )
        return self.async_show_form(
            step_id="rules",
            data_schema=_rules_schema(rules, calendar),
            errors=errors,
            description_placeholders=placeholders,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return RaccoltaOptionsFlow()


class RaccoltaOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        placeholders = {"error": ""}
        options = self.config_entry.options
        rules = dict(options.get(CONF_RULES) or {})
        calendar = options.get(CONF_EXCEPTIONS_CALENDAR)
        if user_input is not None:
            new_rules, errors, placeholders["error"] = _validate(user_input)
            # keep custom (non-standard) types that are not shown in the form
            new_rules = {**{k: v for k, v in rules.items() if k not in TYPE_ORDER}, **new_rules}
            calendar = user_input.get(CONF_EXCEPTIONS_CALENDAR)
            if not errors:
                return self.async_create_entry(
                    data={CONF_RULES: new_rules, CONF_EXCEPTIONS_CALENDAR: calendar}
                )
            rules = new_rules
        return self.async_show_form(
            step_id="init",
            data_schema=_rules_schema(rules, calendar),
            errors=errors,
            description_placeholders=placeholders,
        )
