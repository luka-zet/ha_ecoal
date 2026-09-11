"""Select platform for the eCoal integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EcoalConfigEntry
from .api import EcoalClient
from .const import CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN
from .coordinator import EcoalDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

OPTIONS_ZIMA_LATO = ["Zima", "Lato", "Auto zima/lato"]
# Encja sterująca tryb_auto (zapis): 0=Ręczny, 1=Automatyczny
OPTIONS_TRYB_AUTO = ["Ręczny", "Automatyczny"]

# Map from integer value to string option
MAP_ZIMA_LATO_TO_STR = {
    "0": "Zima",
    "1": "Lato",
    "2": "Auto zima/lato",
}
MAP_STR_TO_ZIMA_LATO = {v: k for k, v in MAP_ZIMA_LATO_TO_STR.items()}

MAP_TRYB_AUTO_TO_STR = {
    "0": "Ręczny",
    "1": "Automatyczny",
}
MAP_STR_TO_TRYB_AUTO = {v: k for k, v in MAP_TRYB_AUTO_TO_STR.items()}


def _parse_zima_lato(data: dict[str, str]) -> str | None:
    """Safely extract zima/lato mode."""
    raw_val = data.get("zima_lato")
    if raw_val is None:
        return None
    return MAP_ZIMA_LATO_TO_STR.get(raw_val)


def _parse_tryb_auto(data: dict[str, str]) -> str | None:
    """Safely extract boiler mode (only for writable modes 0/1).

    Stan "Alarmowy" (2) jest prezentowany przez osobną encję sensor
    (z kluczem tryb_auto_state), ponieważ jest tylko do odczytu.
    """
    raw_val = data.get("tryb_auto_state")
    if raw_val is None:
        return None
    return MAP_TRYB_AUTO_TO_STR.get(raw_val)


@dataclass(frozen=True, kw_only=True)
class EcoalSelectEntityDescription(SelectEntityDescription):
    """Class describing eCoal select entities."""

    value_fn: Callable[[dict[str, str]], str | None]
    set_fn: Callable[[EcoalClient, str], Awaitable[None]]


async def _set_zima_lato(client: EcoalClient, option: str) -> None:
    """Set the zima/lato mode."""
    raw_val = MAP_STR_TO_ZIMA_LATO.get(option)
    if raw_val is not None:
        await client.async_set_register("zima_lato", raw_val)
    else:
        _LOGGER.error("Invalid option for zima_lato: %s", option)


async def _set_tryb_auto(client: EcoalClient, option: str) -> None:
    """Set the boiler mode."""
    raw_val = MAP_STR_TO_TRYB_AUTO.get(option)
    if raw_val is not None:
        # Prawdopodobny rejestr do zapisu to tryb_auto
        await client.async_set_register("tryb_auto", raw_val)
    else:
        _LOGGER.error("Invalid option for tryb_auto: %s", option)


SELECT_DESCRIPTIONS: tuple[EcoalSelectEntityDescription, ...] = (
    EcoalSelectEntityDescription(
        key="zima_lato",
        name="Tryb zima/lato",
        options=OPTIONS_ZIMA_LATO,
        value_fn=_parse_zima_lato,
        set_fn=_set_zima_lato,
    ),
    EcoalSelectEntityDescription(
        key="tryb_auto",
        name="Tryb pracy kotła (sterowanie)",
        options=OPTIONS_TRYB_AUTO,
        value_fn=_parse_tryb_auto,
        set_fn=_set_tryb_auto,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcoalConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up eCoal select entities based on a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        EcoalSelect(coordinator, entry, description)
        for description in SELECT_DESCRIPTIONS
    )


class EcoalSelect(CoordinatorEntity[EcoalDataUpdateCoordinator], SelectEntity):
    """Representation of an eCoal select entity."""

    entity_description: EcoalSelectEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EcoalDataUpdateCoordinator,
        entry: EcoalConfigEntry,
        description: EcoalSelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        port = int(entry.data.get(CONF_PORT, DEFAULT_PORT))
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Sterownik eCoal",
            manufacturer="eCoal",
            model="Sterownik kotła",
            configuration_url=f"http://{entry.data[CONF_HOST]}:{port}",
        )

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.entity_description.set_fn(self.coordinator.client, option)
        # Immediately fetch new data to reflect the change
        await self.coordinator.async_request_refresh()
