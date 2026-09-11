"""Sensor platform for the eCoal integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import EcoalConfigEntry
from .const import CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN
from .coordinator import EcoalDataUpdateCoordinator
from .helpers import parse_float, parse_timestamp

_LOGGER = logging.getLogger(__name__)


# Mapowanie wartości rejestru tryb_auto_state (read-only) na opis tekstowy.
# 0=Ręczny, 1=Automatyczny, 2=Alarmowy (tylko ten rejestr ma stan "2";
# rejestr zapisu tryb_auto przyjmuje tylko 0 lub 1).
_TRYB_AUTO_STATE_MAP: dict[str, str] = {
    "0": "Ręczny",
    "1": "Automatyczny",
    "2": "Alarmowy",
}


def _parse_tryb_auto_state(data: dict[str, str]) -> str | None:
    """Map tryb_auto_state register to a human-readable state.

    Rejestr jest tylko do odczytu i w odróżnieniu od rejestru zapisu
    `tryb_auto` może przyjmować wartość 2 (Alarmowy). Encja
    select 'tryb_auto' służy do sterowania i pomija tę wartość.
    """
    raw_val = data.get("tryb_auto_state")
    if raw_val is None:
        return None
    return _TRYB_AUTO_STATE_MAP.get(raw_val, f"Nieznany ({raw_val})")


@dataclass(frozen=True, kw_only=True)
class EcoalSensorEntityDescription(SensorEntityDescription):
    """Class describing eCoal sensor entities."""

    value_fn: Callable[[dict[str, str]], Any]


SENSOR_DESCRIPTIONS: tuple[EcoalSensorEntityDescription, ...] = (
    # Numeric sensors with temperature class
    EcoalSensorEntityDescription(
        key="t1_value",
        name="Temperatura za zaworem 4D",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: parse_float(data, "t1_value"),
    ),
    EcoalSensorEntityDescription(
        key="tcwu_value",
        name="Temperatura CWU",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: parse_float(data, "tcwu_value"),
    ),
    EcoalSensorEntityDescription(
        key="tkot_value",
        name="Temperatura kotła",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: parse_float(data, "tkot_value"),
    ),
    EcoalSensorEntityDescription(
        key="tsp_value",
        name="Temperatura spalin",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: parse_float(data, "tsp_value"),
    ),
    EcoalSensorEntityDescription(
        key="tpow_value",
        name="Temperatura powrotu",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: parse_float(data, "tpow_value"),
    ),
    # Numeric percentage sensors
    EcoalSensorEntityDescription(
        key="fuel_level",
        name="Poziom paliwa",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: parse_float(data, "fuel_level"),
    ),
    EcoalSensorEntityDescription(
        key="ob1_zaw4d_pos",
        name="Pozycja zaworu 4D",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: parse_float(data, "ob1_zaw4d_pos"),
    ),
    # Timestamp sensor
    EcoalSensorEntityDescription(
        key="next_fuel_time",
        name="Następny zasyp",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: parse_timestamp(data, "next_fuel_time"),
    ),
    # Diagnostyczny sensor trybu pracy kotła (read-only, uwzględnia stan "Alarmowy").
    # Uwaga: key (a więc i unique_id) to "tryb_auto_mode" - NIE "tryb_auto_state"!
    # "tryb_auto_state" jest zarezerwowany dla encji select, która w poprzedniej
    # wersji integracji używała tego klucza; gdyby sensor użył tego samego klucza,
    # Home Assistant zgłosiłby konflikt unique_id i pominął encję.
    EcoalSensorEntityDescription(
        key="tryb_auto_mode",
        name="Aktualny tryb pracy kotła",
        icon="mdi:state-machine",
        value_fn=_parse_tryb_auto_state,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcoalConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up eCoal sensor entities based on a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        EcoalSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class EcoalSensor(CoordinatorEntity[EcoalDataUpdateCoordinator], SensorEntity):
    """Representation of an eCoal sensor."""

    entity_description: EcoalSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EcoalDataUpdateCoordinator,
        entry: EcoalConfigEntry,
        description: EcoalSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
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
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
