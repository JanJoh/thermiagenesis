"""The pump's model is the user's to set; the device's identity never moves."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_MODEL
from homeassistant.const import CONF_PORT
from homeassistant.const import CONF_TYPE
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.thermiagenesis.const import DOMAIN
from custom_components.thermiagenesis.entity import build_device_info
from custom_components.thermiagenesis.entity import configured_model

CONNECTION = {CONF_HOST: "192.0.2.10", CONF_PORT: 502, CONF_TYPE: "mega"}
IDENTIFIER = (DOMAIN, "Diplomat Inverter Duo")


class FakeThermia:
    """Stands in for the Modbus client: answers every read with nothing."""

    def __init__(self, *args, **kwargs):
        self.data = {}

    async def async_update(self, only_registers=None):
        return {}


@pytest.fixture(autouse=True)
def no_modbus(enable_custom_integrations):
    with patch("custom_components.thermiagenesis.ThermiaGenesis", FakeThermia), patch(
        "custom_components.thermiagenesis.config_flow.ThermiaGenesis", FakeThermia
    ):
        yield


def entry_with(data=None, options=None):
    return SimpleNamespace(data=data or {}, options=options or {})


def test_no_model_unless_the_user_gave_one():
    assert configured_model(entry_with()) is None
    assert configured_model(entry_with(data={CONF_MODEL: "  "})) is None


def test_model_from_setup_and_from_options():
    assert configured_model(entry_with(data={CONF_MODEL: "Calibra 8"})) == "Calibra 8"
    both = entry_with(data={CONF_MODEL: "Calibra 8"}, options={CONF_MODEL: " Atlas "})
    assert configured_model(both) == "Atlas"
    # Emptying the field in the options clears a model given at setup.
    cleared = entry_with(data={CONF_MODEL: "Calibra 8"}, options={CONF_MODEL: ""})
    assert configured_model(cleared) is None


def test_device_identity_does_not_follow_the_model():
    coordinator = SimpleNamespace(firmware="17.1.0")
    plain = build_device_info(coordinator, entry_with())
    named = build_device_info(coordinator, entry_with(data={CONF_MODEL: "Sigrin 13"}))
    assert plain["identifiers"] == named["identifiers"] == {IDENTIFIER}
    assert plain["name"] == named["name"] == "Diplomat Inverter Duo"
    assert (plain["model"], named["model"]) == (None, "Sigrin 13")


async def test_setup_stores_the_model(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={**CONNECTION, CONF_MODEL: " Sigrin 13 Duo "}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {**CONNECTION, CONF_MODEL: "Sigrin 13 Duo"}
    await hass.async_block_till_done()


async def test_setup_without_a_model_stores_none(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=dict(CONNECTION)
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == CONNECTION
    await hass.async_block_till_done()


async def test_changing_the_model_keeps_device_and_entities(hass):
    """An install from before the model field: set a model, lose nothing."""
    entry = MockConfigEntry(domain=DOMAIN, data=dict(CONNECTION))
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    devices = dr.async_get(hass)
    entities = er.async_get(hass)
    device = devices.async_get_device(identifiers={IDENTIFIER})
    assert device.model is None
    before = {
        e.unique_id: e.entity_id
        for e in er.async_entries_for_config_entry(entities, entry.entry_id)
    }
    assert before

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_MODEL: "Sigrin 13 Duo"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    assert len(devices.devices) == 1
    same = devices.async_get_device(identifiers={IDENTIFIER})
    assert same.id == device.id
    assert same.model == "Sigrin 13 Duo"
    assert same.name == "Diplomat Inverter Duo"
    after = {
        e.unique_id: e.entity_id
        for e in er.async_entries_for_config_entry(entities, entry.entry_id)
    }
    assert after == before

    # Emptying the field takes the model off the device again.
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={}
    )
    await hass.async_block_till_done()
    assert devices.async_get_device(identifiers={IDENTIFIER}).model is None
