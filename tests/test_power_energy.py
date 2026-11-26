"""Heat demand, power, energy and smart grid sensors (thermia-genesis-modbus 1.1)."""

from types import SimpleNamespace

import thermia_genesis_modbus.const as thermiaconst
from custom_components.thermiagenesis.const import ATTR_CLASS
from custom_components.thermiagenesis.const import ATTR_DEFAULT_ENABLED
from custom_components.thermiagenesis.const import NUMBER_TYPES
from custom_components.thermiagenesis.const import SENSOR_TYPES
from custom_components.thermiagenesis.const import SWITCH_TYPES
from custom_components.thermiagenesis.sensor import ThermiaGenericSensor
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorStateClass
from thermia_genesis_modbus.const import REGISTERS

ENERGY = [
    thermiaconst.ATTR_INPUT_CONSUMED_ELECTRICAL_ENERGY,
    thermiaconst.ATTR_INPUT_DELIVERED_HEAT_ENERGY,
    thermiaconst.ATTR_INPUT_ENERGY_FROM_NATURAL_SOURCE,
]
NEW = ENERGY + [
    thermiaconst.ATTR_INPUT_CALCULATED_DEMAND_HEAT,
    thermiaconst.ATTR_INPUT_CURRENT_POWER_OUTPUT,
    thermiaconst.ATTR_INPUT_CURRENT_CONSUMED_POWER,
    thermiaconst.ATTR_INPUT_REPORTED_COP,
    thermiaconst.ATTR_HOLDING_DESIRED_POWER_CONSUMPTION_CONTROL_MODE,
    thermiaconst.ATTR_HOLDING_INPUT_POWER_LIMIT,
]
COMFORT = thermiaconst.ATTR_INPUT_COMFORT_MODE


def sensor(kind, data):
    return ThermiaGenericSensor(SimpleNamespace(data=data), kind, {})


def test_every_sensor_is_a_register_the_library_knows():
    assert [kind for kind in SENSOR_TYPES if kind not in REGISTERS] == []


def test_new_sensors_are_opt_in():
    for kind in NEW:
        assert SENSOR_TYPES[kind][ATTR_DEFAULT_ENABLED] is False


def test_power_is_reported_in_kilowatts():
    s = sensor(thermiaconst.ATTR_INPUT_CURRENT_CONSUMED_POWER, {})
    assert s.device_class == SensorDeviceClass.POWER
    assert s.unit_of_measurement == "kW"
    assert s.state_class == SensorStateClass.MEASUREMENT


def test_energy_figures_are_not_totals():
    """They fall again, so a total would corrupt the long-term statistics."""
    for kind in ENERGY:
        s = sensor(kind, {kind: 16})
        assert s.state == 16
        assert s.unit_of_measurement == "kWh"
        assert s.state_class == SensorStateClass.MEASUREMENT
        assert ATTR_CLASS not in SENSOR_TYPES[kind]


def test_smart_grid_settings_are_read_only():
    for kind in (
        thermiaconst.ATTR_HOLDING_DESIRED_POWER_CONSUMPTION_CONTROL_MODE,
        thermiaconst.ATTR_HOLDING_INPUT_POWER_LIMIT,
    ):
        assert kind in SENSOR_TYPES
        assert kind not in NUMBER_TYPES
        assert kind not in SWITCH_TYPES


def test_comfort_mode_shows_its_name():
    s = sensor(COMFORT, {COMFORT: 4})
    assert s.state == "Normal"
    assert s.device_class == SensorDeviceClass.ENUM
    assert s.state_class is None
    assert s.options == ["EVU", "Normal", "Comfort", "Boost"]
    assert sensor(COMFORT, {COMFORT: 6}).state == "Boost"


def test_comfort_mode_without_a_name_is_unknown():
    assert sensor(COMFORT, {COMFORT: 2}).state is None
    assert sensor(COMFORT, {}).state is None


def test_plain_sensors_still_report_the_raw_value():
    kind = thermiaconst.ATTR_INPUT_CALCULATED_DEMAND_HEAT
    assert sensor(kind, {kind: -1.01}).state == -1.01
    assert sensor(kind, {kind: 0}).state == 0
