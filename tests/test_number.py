"""Gear-limit numbers follow the compressor's own number of gears."""

from types import SimpleNamespace

import pythermiagenesis.const as thermiaconst
from custom_components.thermiagenesis.number import ThermiaGenericNumber

MAX_HEAT = thermiaconst.ATTR_HOLDING_MAXIMUM_ALLOWED_GEAR_IN_HEATING
GEARS = thermiaconst.ATTR_INPUT_COMPRESSOR_AVAILABLE_GEARS


def number(kind, data):
    return ThermiaGenericNumber(SimpleNamespace(data=data), kind, {})


async def test_gear_limit_follows_available_gears():
    assert number(MAX_HEAT, {GEARS: 10, MAX_HEAT: 10}).native_max_value == 10
    assert number(MAX_HEAT, {GEARS: 7}).native_max_value == 7


async def test_gear_limit_fallback_is_ten():
    assert number(MAX_HEAT, {}).native_max_value == 10
    assert number(MAX_HEAT, {GEARS: None}).native_max_value == 10
    assert number(MAX_HEAT, {GEARS: "x"}).native_max_value == 10
    assert number(MAX_HEAT, None).native_max_value == 10
    assert number(MAX_HEAT, {}).native_min_value == 1


async def test_heating_season_stop_has_outdoor_range():
    n = number(thermiaconst.ATTR_HOLDING_HEATING_SEASON_STOP_TEMPERATURE, {})
    assert (n.native_min_value, n.native_max_value) == (5, 25)


async def test_other_numbers_keep_their_range():
    kind = thermiaconst.ATTR_HOLDING_COMFORT_WHEEL_SETTING
    n = number(kind, {GEARS: 10})
    assert n.native_max_value == n.max
