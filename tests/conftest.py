"""Global fixtures for Thermia Genesis integration."""
from unittest.mock import patch

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"

# test_init.py and test_config_flow.py are cookiecutter-blueprint tests that
# mock a `ThermiaApiClient` the integration never defined. Parked (not
# collected) until rewritten against the real thermia_genesis_modbus client.
collect_ignore = ["test_init.py", "test_config_flow.py"]


# Prevent HomeAssistant from creating/dismissing persistent notifications,
# which would fail since that integration is never loaded during a test.
@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with patch("homeassistant.components.persistent_notification.async_create"), patch(
        "homeassistant.components.persistent_notification.async_dismiss"
    ):
        yield
