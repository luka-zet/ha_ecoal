"""Binary sensor platform for the eCoal integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EcoalConfigEntry
from .const import CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN
from .coordinator import EcoalDataUpdateCoordinator
from .helpers import parse_bool_running

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class EcoalBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Class describing eCoal binary sensor entities."""

    is_on_fn: Callable[[dict[str, str]], bool | None]


BINARY_SENSOR_DESCRIPTIONS: tuple[EcoalBinarySensorEntityDescription, ...] = (
    EcoalBinarySensorEntityDescription(
        key="out_pomp1",
        name="Pompa CO",
        device_class=BinarySensorDeviceClass.RUNNING,
        is_on_fn=lambda data: parse_bool_running(data, "out_pomp1"),
    ),
    EcoalBinarySensorEntityDescription(
        key="out_cwu",
        name="Pompa CWU",
        device_class=BinarySensorDeviceClass.RUNNING,
        is_on_fn=lambda data: parse_bool_running(data, "out_cwu"),
    ),
    EcoalBinarySensorEntityDescription(
        key="out_dm",
        name="Dmuchawa",
        device_class=BinarySensorDeviceClass.RUNNING,
        is_on_fn=lambda data: parse_bool_running(data, "out_dm"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcoalConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up eCoal binary sensor entities based on a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        EcoalBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class EcoalBinarySensor(CoordinatorEntity[EcoalDataUpdateCoordinator], BinarySensorEntity):
    """Representation of an eCoal binary sensor."""

    entity_description: EcoalBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EcoalDataUpdateCoordinator,
        entry: EcoalConfigEntry,
        description: EcoalBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
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
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data:
            return None
        return self.entity_description.is_on_fn(self.coordinator.data)
