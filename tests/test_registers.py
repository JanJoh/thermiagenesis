"""Mega register-table corrections shipped in thermia-genesis-modbus."""

import thermia_genesis_modbus.const as thermiaconst
from thermia_genesis_modbus.const import MODEL_MEGA
from thermia_genesis_modbus.const import REGISTERS

from custom_components.thermiagenesis.const import ATTR_DEFAULT_ENABLED
from custom_components.thermiagenesis.const import BINARY_SENSOR_TYPES
from custom_components.thermiagenesis.const import SENSOR_TYPES


def test_internal_immersion_heater_exists_on_mega():
    step = thermiaconst.ATTR_INPUT_INTERNAL_ADDITIONAL_HEATER_CURRENT_STEP
    active = thermiaconst.ATTR_DINPUT_INTERNAL_ADDITIONAL_HEATER_ACTIVE
    assert REGISTERS[step][MODEL_MEGA] is True
    assert REGISTERS[active][MODEL_MEGA] is True
    assert SENSOR_TYPES[step][ATTR_DEFAULT_ENABLED] is True
    assert BINARY_SENSOR_TYPES[active][ATTR_DEFAULT_ENABLED] is True
