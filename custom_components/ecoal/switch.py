"""Switch platform for the eCoal integration."""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import EcoalConfigEntry
from .const import CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcoalConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up eCoal switch entities based on a config entry."""
    async_add_entities([
        EcoalAutoZimaLatoSwitch(entry),
        EcoalHeatingCurveSwitch(entry),
    ])


class EcoalAutoZimaLatoSwitch(RestoreEntity, SwitchEntity):
    """Virtual switch to enable/disable auto zima/lato mode."""

    _attr_has_entity_name = True
    _attr_name = "Auto zima/lato"
    _attr_icon = "mdi:sun-snowflake-variant"

    def __init__(self, entry: EcoalConfigEntry) -> None:
        """Initialize the switch."""
        self._attr_unique_id = f"{entry.entry_id}_auto_zima_lato"
        self._attr_is_on = False
        port = int(entry.data.get(CONF_PORT, DEFAULT_PORT))
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Sterownik eCoal",
            manufacturer="eCoal",
            model="Sterownik kotła",
            configuration_url=f"http://{entry.data[CONF_HOST]}:{port}",
        )

    async def async_added_to_hass(self) -> None:
        """Restore last known state."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._attr_is_on = last_state.state == "on"

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the switch."""
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the switch."""
        self._attr_is_on = False
        self.async_write_ha_state()


class EcoalHeatingCurveSwitch(RestoreEntity, SwitchEntity):
    """Virtual switch to enable/disable heating curve."""

    _attr_has_entity_name = True
    _attr_name = "Krzywa grzania"
    _attr_icon = "mdi:chart-bell-curve"

    def __init__(self, entry: EcoalConfigEntry) -> None:
        """Initialize the switch."""
        self._attr_unique_id = f"{entry.entry_id}_heating_curve"
        self._attr_is_on = False
        port = int(entry.data.get(CONF_PORT, DEFAULT_PORT))
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Sterownik eCoal",
            manufacturer="eCoal",
            model="Sterownik kotła",
            configuration_url=f"http://{entry.data[CONF_HOST]}:{port}",
        )

    async def async_added_to_hass(self) -> None:
        """Restore last known state."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._attr_is_on = last_state.state == "on"

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the switch."""
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the switch."""
        self._attr_is_on = False
        self.async_write_ha_state()
