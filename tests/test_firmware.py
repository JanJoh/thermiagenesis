"""The device's firmware version follows the pump, not the last restart."""

from unittest.mock import patch

import pytest
from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_PORT
from homeassistant.const import CONF_TYPE
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry
from thermia_genesis_modbus.const import ATTR_INPUT_SOFTWARE_VERSION_MAJOR
from thermia_genesis_modbus.const import ATTR_INPUT_SOFTWARE_VERSION_MICRO
from thermia_genesis_modbus.const import ATTR_INPUT_SOFTWARE_VERSION_MINOR

from custom_components.thermiagenesis import _firmware_of
from custom_components.thermiagenesis.const import DOMAIN

CONNECTION = {CONF_HOST: "192.0.2.10", CONF_PORT: 502, CONF_TYPE: "mega"}
IDENTIFIER = (DOMAIN, "Diplomat Inverter Duo")


def version(major, minor, micro):
    return {
        ATTR_INPUT_SOFTWARE_VERSION_MAJOR: major,
        ATTR_INPUT_SOFTWARE_VERSION_MINOR: minor,
        ATTR_INPUT_SOFTWARE_VERSION_MICRO: micro,
    }


class FakeThermia:
    """Stands in for the Modbus client; reports whatever firmware it is told to."""

    answer = version(17, 3, 145)

    def __init__(self, *args, **kwargs):
        self.data = {}

    async def async_update(self, only_registers=None):
        return dict(type(self).answer)


@pytest.fixture(autouse=True)
def no_modbus(enable_custom_integrations):
    FakeThermia.answer = version(17, 3, 145)
    with patch("custom_components.thermiagenesis.ThermiaGenesis", FakeThermia):
        yield


async def set_up(hass):
    entry = MockConfigEntry(domain=DOMAIN, data=dict(CONNECTION))
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return hass.data[DOMAIN][entry.entry_id]


def test_version_needs_all_three_registers():
    assert _firmware_of(version(18, 0, 20)) == "18.0.20"
    assert _firmware_of({ATTR_INPUT_SOFTWARE_VERSION_MAJOR: 18}) is None
    assert _firmware_of({}) is None
    assert _firmware_of(None) is None


async def test_device_shows_the_firmware_read_at_setup(hass):
    await set_up(hass)
    device = dr.async_get(hass).async_get_device(identifiers={IDENTIFIER})
    assert device.sw_version == "17.3.145"


async def test_a_firmware_update_reaches_the_device_without_a_reload(hass):
    """The pump is updated while Home Assistant runs: the next poll shows it."""
    coordinator = await set_up(hass)
    devices = dr.async_get(hass)
    device = devices.async_get_device(identifiers={IDENTIFIER})

    FakeThermia.answer = version(18, 0, 20)
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    updated = devices.async_get_device(identifiers={IDENTIFIER})
    assert updated.id == device.id
    assert updated.sw_version == "18.0.20"
    assert coordinator.firmware == "18.0.20"


async def test_an_unchanged_version_writes_nothing(hass):
    coordinator = await set_up(hass)
    devices = dr.async_get(hass)
    with patch.object(devices, "async_update_device") as update:
        await coordinator.async_refresh()
        await coordinator.async_refresh()
    update.assert_not_called()


async def test_a_poll_without_the_version_keeps_the_last_one(hass):
    """A read that comes back without the version registers changes nothing."""
    coordinator = await set_up(hass)
    devices = dr.async_get(hass)

    FakeThermia.answer = {}
    await coordinator.async_refresh()
    assert devices.async_get_device(identifiers={IDENTIFIER}).sw_version == "17.3.145"

    # And when the version comes back changed, the change is still noticed.
    FakeThermia.answer = version(18, 0, 20)
    await coordinator.async_refresh()
    assert devices.async_get_device(identifiers={IDENTIFIER}).sw_version == "18.0.20"
