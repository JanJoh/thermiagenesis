"""The ThermiaGenesis component."""
import asyncio
import logging
import time
from datetime import datetime
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_PORT
from homeassistant.const import CONF_TYPE
from homeassistant.helpers.typing import ConfigType
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed
from pythermiagenesis import ThermiaGenesis
from pythermiagenesis.const import ATTR_INPUT_POOL_RETURN_LINE_TEMPERATURE
from pythermiagenesis.const import ATTR_INPUT_POOL_SUPPLY_LINE_TEMPERATURE
from pythermiagenesis.const import KEY_SCALE
from pythermiagenesis.const import MODEL_MEGA
from pythermiagenesis.const import REG_DISCRETE_INPUT
from pythermiagenesis.const import REGISTER_RANGES
from pythermiagenesis.const import REGISTERS

from .const import DOMAIN

# --- Workaround for pythermiagenesis 0.1.8 ---------------------------------
# On the mega platform, four discrete-input registers are flagged
# MODEL_MEGA: True in the library's REGISTERS table -- so the per-model gate in
# our platform setups correctly creates entities for them -- yet they fall
# outside the declared mega dinput ranges, [[0, 3], [9, 83], [199, 247]]:
#
#     addr 4   dinput_alarm_active_class_e
#     addr 84  dinput_primary_unit_conflict_alarm
#     addr 85  dinput_primary_unit_no_secondary_alarm
#     addr 86  dinput_oil_boost_in_progress
#
# Enabling any of them makes _get_data() unable to place the address in a
# block, and the unguarded lookup raises:
#
#     chunk["range_end"] = in_range[0][1]
#     IndexError: list index out of range
#
# That happens inside the coordinator's _async_update_data, so one such
# register fails the entire refresh and every entity the integration owns goes
# unavailable -- not just the offending one.
#
# Confirmed against "Modbus protocol for Mega & Mega E, Genesis platform"
# v17.00.007: the discrete input table runs 0=Class A, 1=B, 2=C,
# 3=D (Genesis secondary), 4=E (Legacy secondary), then jumps to 9 -- so 5-8 is
# a genuine hole -- and the 81..87 block ends at 87 (tap water top sensor
# alarm), which the library's table does not carry. Also verified by read-only
# Modbus probe against a Calibra 8E: all four addresses, and the block read of
# 0-4 this range produces, answer normally.
#
# Upstream: CJNE/pythermiagenesis#7 (these ranges) and #8 (_get_data should
# warn and skip instead of raising). Remove this once #7 is released.
REGISTER_RANGES[MODEL_MEGA][REG_DISCRETE_INPUT] = [[0, 4], [9, 87], [199, 247]]

# Pool supply/return line temperature are declared scale 1, but the Thermia
# spec gives both as scale 100 -- as it does for every other degC register in
# the map. Left uncorrected they report a hundred times too high.
#     input 119  Pool supply line temperature (EM)   degC  scale 100
#     input 120  Pool return line temperature (EM)   degC  scale 100
REGISTERS[ATTR_INPUT_POOL_SUPPLY_LINE_TEMPERATURE][KEY_SCALE] = 100
REGISTERS[ATTR_INPUT_POOL_RETURN_LINE_TEMPERATURE][KEY_SCALE] = 100

PLATFORMS = ["sensor", "binary_sensor", "climate", "switch", "number"]

SCAN_INTERVAL = timedelta(seconds=30)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Set up the ThermiaGenesis component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up ThermiaGenesis from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    kind = entry.data[CONF_TYPE]

    coordinator = ThermiaGenesisDataUpdateCoordinator(
        hass, host=host, port=port, kind=kind
    )
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class ThermiaGenesisDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching ThermiaGenesis data from the heat pump."""

    def __init__(self, hass, host, port, kind):
        """Initialize."""
        self.thermia = ThermiaGenesis(
            host, port=port, kind=kind, delay=0.05, max_registers=16
        )
        self.kind = kind
        self.attributes = {}

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        """Update data via library."""
        data = {}
        try:
            start_time = time.time()
            registers = self.attributes.keys()
            data = await self.thermia.async_update(only_registers=registers)
            # for reg in registers:
            #    #await self.thermia.async_update(only_registers=[reg]) #registers)
            #    print(f"Got {reg}: {self.thermia.data[reg]}")
            _LOGGER.debug(data)
            end_time = time.time()
            _LOGGER.debug(
                f"{datetime.now()} Fetching heatpump data took {end_time - start_time} s"
            )

        except (ConnectionError) as error:
            raise UpdateFailed(error)
        return data

    async def _async_set_data(self, register, value):
        """Set data via library."""
        try:
            await self.thermia.async_set(register, value)
        except (ConnectionError) as error:
            raise UpdateFailed(error)
        return self.thermia.data

    def registerAttribute(self, attribute):
        if type(attribute) is list:
            for name in attribute:
                _LOGGER.info(f"Register attribute for update: {name}")
                self.attributes[name] = True
        else:
            _LOGGER.info(f"Register attribute for update: {attribute}")
            self.attributes[attribute] = True

    async def wantsRefresh(self, attribute):
        await self.coordinator.async_request_refresh()
