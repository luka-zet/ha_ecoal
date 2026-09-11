"""Number platform for the eCoal integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import logging

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import EcoalConfigEntry
from .api import EcoalClient
from .const import CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN
from .coordinator import EcoalDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def _parse_float(data: dict[str, str], key: str) -> float | None:
    """Safely extract and convert register value to float."""
    raw_val = data.get(key)
    if raw_val is None:
        return None
    try:
        return float(raw_val)
    except (ValueError, TypeError):
        return None


@dataclass(frozen=True, kw_only=True)
class EcoalNumberEntityDescription(NumberEntityDescription):
    """Class describing eCoal number entities."""

    value_fn: Callable[[dict[str, str]], float | None]
    set_fn: Callable[[EcoalClient, float], Awaitable[None]]


async def _set_ob1_tzad(client: EcoalClient, value: float) -> None:
    """Set the 4D valve target temperature."""
    # Convert float to int string as the controller expects integer for this
    await client.async_set_register("ob1_tzad", str(int(value)))


async def _set_kot_tzad(client: EcoalClient, value: float) -> None:
    """Set the boiler target temperature."""
    await client.async_set_register("kot_tzad", str(int(value)))


async def _set_cwu_tzad(client: EcoalClient, value: float) -> None:
    """Set the CWU target temperature."""
    await client.async_set_register("cwu_tzad", str(int(value)))


NUMBER_DESCRIPTIONS: tuple[EcoalNumberEntityDescription, ...] = (
    EcoalNumberEntityDescription(
        key="ob1_zaw4d_tzad",
        name="Temperatura 4D zadana",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=20,
        native_max_value=80,
        native_step=1,
        value_fn=lambda data: _parse_float(data, "ob1_zaw4d_tzad"),
        set_fn=_set_ob1_tzad,
    ),
    EcoalNumberEntityDescription(
        key="kot_tzad",
        name="Temperatura kotła zadana",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=40,
        native_max_value=80,
        native_step=1,
        value_fn=lambda data: _parse_float(data, "kot_tzad"),
        set_fn=_set_kot_tzad,
    ),
    EcoalNumberEntityDescription(
        key="cwu_tzad",
        name="Temperatura CWU zadana",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=20,
        native_max_value=60,
        native_step=1,
        value_fn=lambda data: _parse_float(data, "cwu_tzad"),
        set_fn=_set_cwu_tzad,
    ),
)


# --- Virtual number entities (local state, not sent to boiler) ---

@dataclass(frozen=True, kw_only=True)
class EcoalVirtualNumberDescription(NumberEntityDescription):
    """Class describing eCoal virtual number entities."""

    default_value: float


VIRTUAL_NUMBER_DESCRIPTIONS: tuple[EcoalVirtualNumberDescription, ...] = (
    EcoalVirtualNumberDescription(
        key="threshold_lato",
        name="Próg auto lato",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=-10,
        native_max_value=40,
        native_step=0.5,
        icon="mdi:thermometer-chevron-up",
        default_value=15.0,
    ),
    EcoalVirtualNumberDescription(
        key="threshold_zima",
        name="Próg auto zima",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=-10,
        native_max_value=40,
        native_step=0.5,
        icon="mdi:thermometer-chevron-down",
        default_value=10.0,
    ),
    EcoalVirtualNumberDescription(
        key="heating_curve_temp_min",
        name="Krzywa grzania - temp. dla minus 10°C",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=20,
        native_max_value=80,
        native_step=1,
        icon="mdi:thermometer-chevron-up",
        default_value=50.0,
    ),
    EcoalVirtualNumberDescription(
        key="heating_curve_temp_max",
        name="Krzywa grzania - temp. dla plus 10°C",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=20,
        native_max_value=80,
        native_step=1,
        icon="mdi:thermometer-chevron-down",
        default_value=30.0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcoalConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up eCoal number entities based on a config entry."""
    coordinator = entry.runtime_data
    entities: list[NumberEntity] = [
        EcoalNumber(coordinator, entry, description)
        for description in NUMBER_DESCRIPTIONS
    ]
    entities.extend(
        EcoalVirtualNumber(entry, description)
        for description in VIRTUAL_NUMBER_DESCRIPTIONS
    )
    async_add_entities(entities)


class EcoalNumber(CoordinatorEntity[EcoalDataUpdateCoordinator], NumberEntity):
    """Representation of an eCoal number entity."""

    entity_description: EcoalNumberEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EcoalDataUpdateCoordinator,
        entry: EcoalConfigEntry,
        description: EcoalNumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
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
    def native_value(self) -> float | None:
        """Return the state of the entity."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        await self.entity_description.set_fn(self.coordinator.client, value)
        # Immediately fetch new data to reflect the change
        await self.coordinator.async_request_refresh()


class EcoalVirtualNumber(RestoreEntity, NumberEntity):
    """Virtual number entity that stores its value locally (not on the boiler)."""

    entity_description: EcoalVirtualNumberDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        entry: EcoalConfigEntry,
        description: EcoalVirtualNumberDescription,
    ) -> None:
        """Initialize the virtual number entity."""
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_native_value = description.default_value
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
        if last_state is not None and last_state.state not in ("unknown", "unavailable"):
            try:
                self._attr_native_value = float(last_state.state)
            except (ValueError, TypeError):
                pass

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._attr_native_value = value
        self.async_write_ha_state()