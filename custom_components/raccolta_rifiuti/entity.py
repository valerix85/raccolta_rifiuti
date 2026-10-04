# Creato da domoticafacile.it
"""Common base for the entities of the UI (config entry) mode."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, IMAGE_BASE_PATH
from .coordinator import RaccoltaCoordinator
from .localization import DEFAULT_IMAGE, LABELS, STRINGS, TYPE_IMAGES, resolve_language


class RaccoltaEntity(CoordinatorEntity[RaccoltaCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: RaccoltaCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="DomoticaFacile / Unlead",
            model="Raccolta Rifiuti",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def lang(self) -> str:
        return resolve_language(self.hass.config.language if self.hass else None)

    def label(self, code: str) -> str:
        return LABELS[self.lang].get(code) or code.replace("_", " ").capitalize()

    def labels(self, codes: list[str]) -> list[str]:
        return [self.label(c) for c in codes]

    def text(self, key: str) -> str:
        return STRINGS[self.lang][key]


def picture(codes: list[str]) -> str:
    image = next((TYPE_IMAGES[c] for c in codes if c in TYPE_IMAGES), DEFAULT_IMAGE)
    return f"{IMAGE_BASE_PATH}{image}"


def join_it(items: list[str], conj: str) -> str:
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} {conj} {items[-1]}"
