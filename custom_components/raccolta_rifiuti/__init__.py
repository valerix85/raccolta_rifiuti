# Creato da domoticafacile.it
"""Raccolta Rifiuti: waste collection sensor based on a calendar."""
from __future__ import annotations

import logging
import os
import shutil

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN  # noqa: F401  (re-exported for convenience)

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
    """Set up the integration (YAML only, see sensor platform)."""
    await hass.async_add_executor_job(_copy_images, hass)
    return True
