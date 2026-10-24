"""Register-table corrections applied by the integration on import."""

import pythermiagenesis.const as thermiaconst
from pythermiagenesis.const import MODEL_MEGA, REGISTERS

import custom_components.thermiagenesis  # noqa: F401  (applies the patches)
from custom_components.thermiagenesis.const import ATTR_DEFAULT_ENABLED, BINARY_SENSOR_TYPES, SENSOR_TYPES


def test_internal_immersion_heater_exists_on_mega():
    step = thermiaconst.ATTR_INPUT_INTERNAL_ADDITIONAL_HEATER_CURRENT_STEP
    active = thermiaconst.ATTR_DINPUT_INTERNAL_ADDITIONAL_HEATER_ACTIVE
    assert REGISTERS[step][MODEL_MEGA] is True
    assert REGISTERS[active][MODEL_MEGA] is True
    assert SENSOR_TYPES[step][ATTR_DEFAULT_ENABLED] is True
    assert BINARY_SENSOR_TYPES[active][ATTR_DEFAULT_ENABLED] is True
