import pathlib
import sys

import pytest

# Make sure "custom_components" resolves to this repository (and not to the
# testing_config shipped with pytest-homeassistant-custom-component).
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for mod in [m for m in sys.modules if m == "custom_components" or m.startswith("custom_components.")]:
    del sys.modules[mod]
import custom_components  # noqa: E402,F401

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
