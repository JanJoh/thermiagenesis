"""Demand registers are enum sensors, so their history shows as a timeline."""
from types import SimpleNamespace

import pythermiagenesis.const as thermiaconst
from custom_components.thermiagenesis.const import SENSOR_TYPES
from custom_components.thermiagenesis.sensor import STATUS_OPTIONS
from custom_components.thermiagenesis.sensor import ThermiaGenericSensor
from custom_components.thermiagenesis.sensor import ThermiaHeatpumpSensor
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorStateClass

FIRST = thermiaconst.ATTR_INPUT_FIRST_PRIORITISED_DEMAND
STATUS_KINDS = [
    kind
    for kind in SENSOR_TYPES
    if thermiaconst.REGISTERS[kind][thermiaconst.KEY_DATATYPE]
    == thermiaconst.TYPE_STATUS
]


def sensor(kind, data=None):
    return ThermiaGenericSensor(SimpleNamespace(data=data or {}), kind, {})


async def test_demand_sensors_are_enums():
    assert FIRST in STATUS_KINDS
    assert len(STATUS_KINDS) == 8
    for kind in STATUS_KINDS:
        s = sensor(kind)
        assert s.device_class == SensorDeviceClass.ENUM
        assert s.state_class is None
        assert s.options == STATUS_OPTIONS
        assert s.unit_of_measurement is None


async def test_heatpump_sensor_is_an_enum():
    s = ThermiaHeatpumpSensor(SimpleNamespace(data={}), FIRST, {})
    assert s.device_class == SensorDeviceClass.ENUM
    assert s.state_class is None
    assert s.options == STATUS_OPTIONS


async def test_status_text_is_an_option():
    s = sensor(FIRST, {FIRST: "Anti legionella"})
    assert s.state in s.options


async def test_numeric_sensors_are_unchanged():
    kind = thermiaconst.ATTR_INPUT_COMPRESSOR_AVAILABLE_GEARS
    s = sensor(kind)
    assert s.device_class is None
    assert s.state_class == SensorStateClass.MEASUREMENT
    assert s.options is None
