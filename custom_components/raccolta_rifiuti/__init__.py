# Creato da domoticafacile.it
import os
import shutil
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)
DOMAIN = "raccolta_rifiuti"


def _copy_images(hass: HomeAssistant) -> None:
    """Copy the bundled waste-type images into config/www/.

    Runs in an executor thread (blocking file I/O must never run on the
    event loop). Files are always (re)copied with shutil.copy2, so that
    icons updated in a new integration release also reach installations
    that already had the folder from a previous version - previously the
    copy only ran once and updated icons were never picked up.
    """
    source_dir = os.path.join(os.path.dirname(__file__), "images", "img_raccolta_rifiuti")
    target_dir = os.path.join(hass.config.path("www"), "images", "img_raccolta_rifiuti")

    if not os.path.exists(source_dir):
        _LOGGER.warning(
            "Cartella immagini non trovata in %s: le icone dei rifiuti non saranno "
            "disponibili, ma il sensore continuerà a funzionare normalmente.",
            source_dir,
        )
        return

    os.makedirs(target_dir, exist_ok=True)

    for file_name in os.listdir(source_dir):
        source_file = os.path.join(source_dir, file_name)
        target_file = os.path.join(target_dir, file_name)
        if not os.path.isfile(source_file):
            continue
        try:
            shutil.copy2(source_file, target_file)
            _LOGGER.debug("Copiato %s in %s", file_name, target_dir)
        except OSError as err:
            _LOGGER.warning("Impossibile copiare %s in %s: %s", file_name, target_dir, err)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the raccolta_rifiuti component."""
    await hass.async_add_executor_job(_copy_images, hass)
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry) -> bool:
    return True
