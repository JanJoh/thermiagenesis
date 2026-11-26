"""ThermiaGenesisEntity class"""

import logging

from homeassistant.const import CONF_MODEL
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_MANUFACTURER
from .const import DOMAIN

# The device's identifier and the name the integration gives it. Both stay fixed
# whatever the pump really is: the identifier ties the registry entry -- and with
# it every entity, its history and its statistics -- to the device, and entity IDs
# on many installs carry the name (sensor.diplomat_inverter_duo_*). The real model
# goes in the device's model field instead, see configured_model().
DEVICE_NAME = "Diplomat Inverter Duo"

_LOGGER: logging.Logger = logging.getLogger(__package__)


def configured_model(config_entry):
    """Return the model the user entered, or None if there is none.

    Setup stores it in the entry's data, the options flow in its options; the
    options win, so an emptied field there clears a model given at setup.
    """
    options = getattr(config_entry, "options", None) or {}
    data = getattr(config_entry, "data", None) or {}
    model = options[CONF_MODEL] if CONF_MODEL in options else data.get(CONF_MODEL)
    return (model or "").strip() or None


def build_device_info(coordinator, config_entry):
    """Return the device info every entity of this config entry shares."""
    return {
        "identifiers": {(DOMAIN, DEVICE_NAME)},
        "name": DEVICE_NAME,
        "manufacturer": ATTR_MANUFACTURER,
        "model": configured_model(config_entry),
        "sw_version": coordinator.firmware,
    }


class ThermiaGenesisEntity(CoordinatorEntity):
    def __init__(self, coordinator, config_entry, kind, meta=None):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.config_entry = config_entry
        if meta is None:
            self.meta = {"attrs": {}}
        else:
            self.meta = meta
            if self.meta.get("category", None) is not None:
                self.meta["category"] = EntityCategory(self.meta["category"])

    @property
    def device_info(self):
        return build_device_info(self.coordinator, self.config_entry)

    @property
    def entity_category(self):
        return self.meta.get("category", None)

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            "integration": DOMAIN,
        }
        return {**attrs, **self.meta["attrs"]}


class HeatpumpEntity(CoordinatorEntity):
    def __init__(self, coordinator, config_entry, kind, meta=None):
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.coordinator = coordinator
        if meta is None:
            self.meta = {"attrs": {}}
        else:
            self.meta = meta
        if meta is not None:
            if self.meta.get("category", None) is not None:
                self.meta["category"] = EntityCategory(self.meta["category"])

    @property
    def device_info(self):
        return build_device_info(self.coordinator, self.config_entry)

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            "integration": DOMAIN,
        }
        return {**attrs, **self.meta["attrs"]}

    @property
    def entity_category(self):
        return self.meta.get("category", None)
