# Creato da domoticafacile.it
"""Raccolta Rifiuti: waste collection sensor based on a calendar."""
from __future__ import annotations

import logging
import os
import shutil

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS_ENTRY
from .coordinator import RaccoltaCoordinator

# YAML is still supported for the sensor platform (legacy mode); the
# integration itself has no top-level YAML configuration.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type RaccoltaConfigEntry = ConfigEntry[RaccoltaCoordinator]

_LOGGER = logging.getLogger(__name__)


def _copy_images(hass: HomeAssistant) -> None:
    """Copy the bundled icons into config/www/images/img_raccolta_rifiuti.

    Runs in an executor thread. A file is (re)copied only when it is missing
    or when the bundled one is newer: new icons shipped with an update still
    arrive, but an icon the user replaced by hand (which is newer than the
    bundled one) is no longer overwritten at every restart.
    """
    source_dir = os.path.join(os.path.dirname(__file__), "images", "img_raccolta_rifiuti")
    target_dir = hass.config.path("www", "images", "img_raccolta_rifiuti")

    if not os.path.isdir(source_dir):
        _LOGGER.warning(
            "Cartella immagini non trovata in %s: le icone non saranno disponibili, "
            "il sensore funziona comunque",
            source_dir,
        )
        return

    try:
        os.makedirs(target_dir, exist_ok=True)
    except OSError as err:
        _LOGGER.warning("Impossibile creare %s: %s", target_dir, err)
        return

    for file_name in os.listdir(source_dir):
        source_file = os.path.join(source_dir, file_name)
        target_file = os.path.join(target_dir, file_name)
        if not os.path.isfile(source_file):
            continue
        try:
            if os.path.exists(target_file) and (
                os.path.getmtime(target_file) >= os.path.getmtime(source_file)
            ):
                continue
            shutil.copy2(source_file, target_file)
            _LOGGER.debug("Copiato %s in %s", file_name, target_dir)
        except OSError as err:
            _LOGGER.warning("Impossibile copiare %s in %s: %s", file_name, target_dir, err)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Copy the icons; YAML sensor platform and config entries set up separately."""
    await hass.async_add_executor_job(_copy_images, hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: RaccoltaConfigEntry) -> bool:
    """Set up the rule-based mode created from the UI."""
    coordinator = RaccoltaCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    coordinator.async_setup_listeners()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS_ENTRY)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass: HomeAssistant, entry: RaccoltaConfigEntry) -> None:
    """Rules changed: refresh in place, reload only if the set of types changed."""
    coordinator = entry.runtime_data
    before = set(coordinator.active_types)
    calendar_before = coordinator.calendar_id
    coordinator.load_options()
    if set(coordinator.active_types) != before or coordinator.calendar_id != calendar_before:
        await hass.config_entries.async_reload(entry.entry_id)
        return
    await coordinator.async_refresh()
    coordinator.async_update_listeners()


async def async_unload_entry(hass: HomeAssistant, entry: RaccoltaConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS_ENTRY)
