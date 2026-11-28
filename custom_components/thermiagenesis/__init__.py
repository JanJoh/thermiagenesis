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
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.update_coordinator import UpdateFailed
from thermia_genesis_modbus import ThermiaGenesis
from thermia_genesis_modbus.const import ATTR_INPUT_SOFTWARE_VERSION_MAJOR
from thermia_genesis_modbus.const import ATTR_INPUT_SOFTWARE_VERSION_MICRO
from thermia_genesis_modbus.const import ATTR_INPUT_SOFTWARE_VERSION_MINOR

from .const import DOMAIN
from .entity import DEVICE_NAME

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

    # Ask for the software version registers before the first refresh. The
    # coordinator only reads registers that entities have registered, and no
    # entity exists yet -- so without this the first refresh requests nothing,
    # and thermia.firmware is never populated for the device_info that the
    # platforms build a moment later.
    coordinator.registerAttribute(
        [
            ATTR_INPUT_SOFTWARE_VERSION_MAJOR,
            ATTR_INPUT_SOFTWARE_VERSION_MINOR,
            ATTR_INPUT_SOFTWARE_VERSION_MICRO,
        ]
    )
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Refresh again now that the platforms have registered everything they
    # want. Entities are added with async_add_entities(..., False), so without
    # this every entity reports "unknown" until the next scheduled poll -- up
    # to SCAN_INTERVAL seconds after each setup or reload.
    await coordinator.async_refresh()

    entry.async_on_unload(entry.add_update_listener(_async_reload_on_update))

    return True


async def _async_reload_on_update(hass: HomeAssistant, entry: ConfigEntry):
    """Reload so a model changed in the options reaches the device registry."""
    await hass.config_entries.async_reload(entry.entry_id)


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


def _firmware_of(data):
    """Return the firmware version in a set of register values, or None."""
    data = data or {}
    try:
        return (
            f"{data[ATTR_INPUT_SOFTWARE_VERSION_MAJOR]}"
            f".{data[ATTR_INPUT_SOFTWARE_VERSION_MINOR]}"
            f".{data[ATTR_INPUT_SOFTWARE_VERSION_MICRO]}"
        )
    except KeyError:
        return None


class ThermiaGenesisDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching ThermiaGenesis data from the heat pump."""

    def __init__(self, hass, host, port, kind):
        """Initialize."""
        self.thermia = ThermiaGenesis(
            host, port=port, kind=kind, delay=0.05, max_registers=16
        )
        self.kind = kind
        self.attributes = {}
        # The firmware version last read from the pump, to notice when it changes.
        self._seen_firmware = None

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

        except ConnectionError as error:
            raise UpdateFailed(error)
        self._note_firmware(_firmware_of(data))
        return data

    def _note_firmware(self, firmware):
        """Keep the device registry in step with the pump's firmware.

        The version registers are read on every poll, but the device registry
        only heard about the version when the entities were set up. A pump
        updated while Home Assistant was running kept showing its old firmware
        until the next restart or reload.
        """
        if firmware is None:
            return
        previous, self._seen_firmware = self._seen_firmware, firmware
        if previous is None or previous == firmware:
            return
        _LOGGER.info("Pump firmware changed from %s to %s", previous, firmware)
        registry = dr.async_get(self.hass)
        device = registry.async_get_device(identifiers={(DOMAIN, DEVICE_NAME)})
        if device is not None:
            registry.async_update_device(device.id, sw_version=firmware)

    async def _async_set_data(self, register, value):
        """Set data via library."""
        try:
            await self.thermia.async_set(register, value)
        except ConnectionError as error:
            raise UpdateFailed(error)
        return self.thermia.data

    @property
    def firmware(self):
        """Return the pump firmware version, or None if not yet read.

        Deliberately computed here rather than read from
        ThermiaGenesis.firmware. The library sets that attribute from
        self.data *before* overwriting self.data with the freshly read
        values, so it always lags one refresh behind -- on the first refresh
        self.data is still empty, the KeyError is swallowed by the library's
        own except KeyError, and the attribute stays None. device_info is
        built between those two refreshes, so it would never see a value.
        """
        return _firmware_of(self.data)

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
