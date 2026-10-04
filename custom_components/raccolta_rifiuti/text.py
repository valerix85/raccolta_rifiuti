# Creato da domoticafacile.it
"""Text entities to edit the rules from a dashboard, like the HassioHelp package."""
from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_RULES, DOMAIN
from .coordinator import RaccoltaCoordinator
from .entity import RaccoltaEntity
from .localization import TYPE_ORDER
from .schedule import validate_rule


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: RaccoltaCoordinator = entry.runtime_data
    codes = list(TYPE_ORDER) + [c for c in coordinator.rule_text if c not in TYPE_ORDER]
    async_add_entities(RuleText(coordinator, code) for code in codes)


class RuleText(RaccoltaEntity, TextEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_max = 120
    _attr_icon = "mdi:calendar-edit"

    def __init__(self, coordinator: RaccoltaCoordinator, code: str) -> None:
        super().__init__(coordinator, f"rule_{code}")
        self._code = code
        self._attr_translation_key = f"rule_{code}" if code in TYPE_ORDER else "rule_custom"
        self._attr_translation_placeholders = {"type": code.capitalize()}

    @property
    def native_value(self) -> str:
        return self.coordinator.rule_text.get(self._code, "")

    async def async_set_value(self, value: str) -> None:
        value = value.strip()
        if error := validate_rule(value):
            raise ServiceValidationError(
                f"Regola non valida: {error}",
                translation_domain=DOMAIN,
                translation_key="invalid_rule",
                translation_placeholders={"error": error},
            )
        entry = self.coordinator.config_entry
        rules = dict(entry.options.get(CONF_RULES) or {})
        rules[self._code] = value
        self.hass.config_entries.async_update_entry(
            entry, options={**entry.options, CONF_RULES: rules}
        )
