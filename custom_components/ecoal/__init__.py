"""The eCoal boiler integration."""

from __future__ import annotations

import logging

try:
    import voluptuous as vol
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.const import Platform, STATE_UNAVAILABLE, STATE_UNKNOWN
    from homeassistant.core import Event, HomeAssistant, ServiceCall, callback
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    from homeassistant.helpers.event import async_track_state_change_event
    from homeassistant.helpers import entity_registry as er

    PLATFORMS: list[Platform] = [
        Platform.SENSOR,
        Platform.BINARY_SENSOR,
        Platform.NUMBER,
        Platform.SELECT,
        Platform.SWITCH,
    ]
except ImportError:  # pragma: no cover
    vol = None  # type: ignore[assignment]
    ConfigEntry = object  # type: ignore[assignment, misc]
    HomeAssistant = object  # type: ignore[assignment, misc]
    Event = object  # type: ignore[assignment, misc]
    ServiceCall = object  # type: ignore[assignment, misc]
    callback = lambda f: f  # type: ignore[assignment, misc]
    async_get_clientsession = None  # type: ignore[assignment]
    async_track_state_change_event = None  # type: ignore[assignment]
    STATE_UNAVAILABLE = "unavailable"
    STATE_UNKNOWN = "unknown"
    PLATFORMS = []  # type: ignore[assignment]

from .api import EcoalClient
from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    CONF_EXT_TEMP_SENSOR,
    DEFAULT_PORT,
    DOMAIN,
)
from .coordinator import EcoalDataUpdateCoordinator

type EcoalConfigEntry = ConfigEntry[EcoalDataUpdateCoordinator]

_LOGGER = logging.getLogger(__name__)

SERVICE_ADD_FUEL = "add_fuel"
SERVICE_SET_TIME_TO_EMPTY = "set_time_to_empty"
CONF_FUEL = "fuel"
CONF_TIME_TO_EMPTY = "time_to_empty"

if vol is not None:
    ADD_FUEL_SCHEMA = vol.Schema({vol.Required(CONF_FUEL): vol.Coerce(float)})
    SET_TIME_TO_EMPTY_SCHEMA = vol.Schema({vol.Required(CONF_TIME_TO_EMPTY): vol.Coerce(float)})


def _setup_services(hass: HomeAssistant) -> None:
    """Register custom services for eCoal."""
    if not hasattr(hass, "services") or hass.services.has_service(DOMAIN, SERVICE_ADD_FUEL):
        return

    async def _async_handle_add_fuel(call: ServiceCall) -> None:
        fuel = call.data[CONF_FUEL]
        val_str = str(int(fuel)) if fuel == int(fuel) else str(fuel)
        for entry in hass.config_entries.async_entries(DOMAIN):
            if hasattr(entry, "runtime_data") and entry.runtime_data:
                coord: EcoalDataUpdateCoordinator = entry.runtime_data
                await coord.client.async_set_register("add_fuel", val_str)
                await coord.async_request_refresh()

    async def _async_handle_set_time_to_empty(call: ServiceCall) -> None:
        time_to_empty = call.data[CONF_TIME_TO_EMPTY]
        val_str = str(int(time_to_empty)) if time_to_empty == int(time_to_empty) else str(time_to_empty)
        for entry in hass.config_entries.async_entries(DOMAIN):
            if hasattr(entry, "runtime_data") and entry.runtime_data:
                coord: EcoalDataUpdateCoordinator = entry.runtime_data
                await coord.client.async_set_register("time_to_empty", val_str)
                await coord.async_request_refresh()

    hass.services.async_register(DOMAIN, SERVICE_ADD_FUEL, _async_handle_add_fuel, schema=ADD_FUEL_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SET_TIME_TO_EMPTY, _async_handle_set_time_to_empty, schema=SET_TIME_TO_EMPTY_SCHEMA)


async def async_setup_entry(hass: HomeAssistant, entry: EcoalConfigEntry) -> bool:
    """Set up eCoal from a config entry."""
    session = async_get_clientsession(hass)
    port = int(entry.data.get(CONF_PORT, DEFAULT_PORT))
    client = EcoalClient(
        host=entry.data[CONF_HOST],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        session=session,
        port=port,
    )

    coordinator = EcoalDataUpdateCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Rejestracja usług
    _setup_services(hass)

    # Rejestracja listenera przy zmianie opcji
    entry.async_on_unload(entry.add_update_listener(update_listener))

    # Inicjalizacja automatycznego trybu Zima/Lato
    _setup_auto_zima_lato(hass, entry, client, coordinator)

    # Inicjalizacja krzywej grzania
    _setup_heating_curve(hass, entry, client, coordinator)

    return True


async def update_listener(hass: HomeAssistant, entry: EcoalConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


def _setup_auto_zima_lato(
    hass: HomeAssistant,
    entry: EcoalConfigEntry,
    client: EcoalClient,
    coordinator: EcoalDataUpdateCoordinator,
) -> None:
    """Set up the automatic summer/winter mode based on external sensor.

    Reads config from virtual entities on the device:
    - switch.<entry_id>_auto_zima_lato  (on/off)
    - number.<entry_id>_threshold_lato  (temperature threshold)
    - number.<entry_id>_threshold_zima  (temperature threshold)
    And from config entry options:
    - ext_temp_sensor  (entity_id of the external temperature sensor)
    """
    sensor_id = entry.options.get(CONF_EXT_TEMP_SENSOR)
    if not sensor_id:
        return

    ent_reg = er.async_get(hass)
    switch_entity_id = ent_reg.async_get_entity_id("switch", DOMAIN, f"{entry.entry_id}_auto_zima_lato") or f"switch.sterownik_ecoal_auto_zima_lato"
    threshold_lato_entity_id = ent_reg.async_get_entity_id("number", DOMAIN, f"{entry.entry_id}_threshold_lato") or f"number.sterownik_ecoal_prog_auto_lato"
    threshold_zima_entity_id = ent_reg.async_get_entity_id("number", DOMAIN, f"{entry.entry_id}_threshold_zima") or f"number.sterownik_ecoal_prog_auto_zima"

    async def _state_changed_listener(event: Event | None = None) -> None:
        """Handle external temperature sensor or settings changes."""
        _LOGGER.debug("Auto zima/lato: sprawdzanie warunków")
        
        # Check if auto mode is enabled
        switch_state = hass.states.get(switch_entity_id)
        _LOGGER.debug("Auto zima/lato: stan przełącznika '%s' = %s", switch_entity_id, switch_state)
        if switch_state is None or switch_state.state != "on":
            _LOGGER.debug("Auto zima/lato: przełącznik wyłączony, pomijam")
            return

        sensor_state = hass.states.get(sensor_id)
        if sensor_state is None or sensor_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            _LOGGER.debug("Auto zima/lato: stan czujnika zewn. niedostępny, pomijam")
            return

        try:
            temp = float(sensor_state.state)
        except (ValueError, TypeError):
            _LOGGER.debug("Auto zima/lato: nie mogę sparsować temperatury zewn.: %s", sensor_state.state)
            return

        # Read thresholds from virtual number entities
        threshold_lato = 15.0
        threshold_zima = 10.0

        lato_state = hass.states.get(threshold_lato_entity_id)
        _LOGGER.debug("Auto zima/lato: stan progu lato '%s' = %s", threshold_lato_entity_id, lato_state)
        if lato_state is not None and lato_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                threshold_lato = float(lato_state.state)
            except (ValueError, TypeError):
                pass

        zima_state = hass.states.get(threshold_zima_entity_id)
        _LOGGER.debug("Auto zima/lato: stan progu zima '%s' = %s", threshold_zima_entity_id, zima_state)
        if zima_state is not None and zima_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                threshold_zima = float(zima_state.state)
            except (ValueError, TypeError):
                pass

        _LOGGER.debug(
            "Auto zima/lato: temp=%.1f, próg_lato=%.1f, próg_zima=%.1f",
            temp, threshold_lato, threshold_zima,
        )

        target_mode = None
        if temp >= threshold_lato:
            target_mode = "1"  # Lato
        elif temp <= threshold_zima:
            target_mode = "0"  # Zima

        if target_mode is None:
            _LOGGER.debug("Auto zima/lato: temperatura pomiędzy progami, brak akcji")
            return

        # Sprawdź obecny tryb w koordynatorze, aby uniknąć zbędnych zapytań
        current_mode = coordinator.data.get("zima_lato") if coordinator.data else None
        _LOGGER.debug("Auto zima/lato: obecny tryb=%s, docelowy=%s", current_mode, target_mode)
        if current_mode != target_mode:
            _LOGGER.info(
                "Automatyczna zmiana trybu Zima/Lato na %s (temp. zewn. %.1f°C, próg lato=%.1f, próg zima=%.1f)",
                "Lato" if target_mode == "1" else "Zima",
                temp,
                threshold_lato,
                threshold_zima,
            )
            try:
                await client.async_set_register("zima_lato", target_mode)
                await coordinator.async_request_refresh()
            except Exception as err:
                _LOGGER.error("Błąd podczas automatycznej zmiany trybu Zima/Lato: %s", err)

    if async_track_state_change_event:
        entities_to_track = [sensor_id, switch_entity_id, threshold_lato_entity_id, threshold_zima_entity_id]
        unsub = async_track_state_change_event(
            hass, entities_to_track, _state_changed_listener
        )
        entry.async_on_unload(unsub)


def _setup_heating_curve(
    hass: HomeAssistant,
    entry: EcoalConfigEntry,
    client: EcoalClient,
    coordinator: EcoalDataUpdateCoordinator,
) -> None:
    """Set up automatic heating curve adjustment.

    Reads config from virtual entities on the device:
    - switch.<entry_id>_heating_curve  (on/off)
    - number.<entry_id>_heating_curve_temp_min  (temperature for -10°C)
    - number.<entry_id>_heating_curve_temp_max  (temperature for +10°C)
    And from config entry options:
    - ext_temp_sensor  (entity_id of the external temperature sensor)
    """
    sensor_id = entry.options.get(CONF_EXT_TEMP_SENSOR)
    if not sensor_id:
        return

    ent_reg = er.async_get(hass)
    switch_entity_id = ent_reg.async_get_entity_id("switch", DOMAIN, f"{entry.entry_id}_heating_curve") or f"switch.sterownik_ecoal_krzywa_grzania"
    temp_min_entity_id = ent_reg.async_get_entity_id("number", DOMAIN, f"{entry.entry_id}_heating_curve_temp_min") or f"number.sterownik_ecoal_krzywa_grzania_temp_dla_minus_10c"
    temp_max_entity_id = ent_reg.async_get_entity_id("number", DOMAIN, f"{entry.entry_id}_heating_curve_temp_max") or f"number.sterownik_ecoal_krzywa_grzania_temp_dla_plus_10c"

    async def _heating_curve_listener(event: Event | None = None) -> None:
        """Handle temperature or setting changes for heating curve."""
        _LOGGER.debug("Krzywa grzania: sprawdzanie warunków")

        switch_state = hass.states.get(switch_entity_id)
        if switch_state is None or switch_state.state != "on":
            _LOGGER.debug("Krzywa grzania: przełącznik wyłączony, pomijam")
            return

        sensor_state = hass.states.get(sensor_id)
        if sensor_state is None or sensor_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            _LOGGER.debug("Krzywa grzania: stan czujnika zewn. niedostępny, pomijam")
            return

        try:
            outdoor_temp = float(sensor_state.state)
        except (ValueError, TypeError):
            _LOGGER.debug("Krzywa grzania: nie mogę sparsować temperatury zewn.: %s", sensor_state.state)
            return

        temp_min = 50.0
        temp_max = 30.0

        min_state = hass.states.get(temp_min_entity_id)
        if min_state is not None and min_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                temp_min = float(min_state.state)
            except (ValueError, TypeError):
                pass

        max_state = hass.states.get(temp_max_entity_id)
        if max_state is not None and max_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            try:
                temp_max = float(max_state.state)
            except (ValueError, TypeError):
                pass

        target_temp = _calculate_heating_curve(outdoor_temp, temp_min, temp_max)
        target_temp_int = int(round(target_temp))

        # Ograniczenie ilości zapytań - sprawdźmy obecną wartość w koordynatorze
        current_target_raw = coordinator.data.get("ob1_zaw4d_tzad") if coordinator.data else None
        current_target = float(current_target_raw) if current_target_raw is not None else None

        if current_target is not None and int(current_target) == target_temp_int:
            _LOGGER.debug("Krzywa grzania: temperatura zaworu 4D jest już ustawiona na %d°C, pomijam", target_temp_int)
            return

        _LOGGER.info(
            "Krzywa grzania: ustawiam temperaturę zaworu 4D na %d°C dla temp. zewn. %.1f°C",
            target_temp_int, outdoor_temp,
        )

        try:
            # Set the 4D valve target temperature
            from .number import _set_ob1_tzad
            await _set_ob1_tzad(client, float(target_temp_int))
            await coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Błąd podczas ustawiania krzywej grzania: %s", err)

    if async_track_state_change_event:
        # Nasłuchuj zmian na wszystkich powiązanych encjach
        entities_to_track = [sensor_id, switch_entity_id, temp_min_entity_id, temp_max_entity_id]
        unsub = async_track_state_change_event(
            hass, entities_to_track, _heating_curve_listener
        )
        entry.async_on_unload(unsub)


def _calculate_heating_curve(
    outdoor_temp: float,
    temp_min: float,
    temp_max: float,
) -> float:
    """
    Calculate target temperature based on heating curve.

    Krzywa grzania jest linią prostą między punktami:
    - Przy -10°C -> temp_min
    - Przy +10°C -> temp_max
    
    Temperatura zewnętrzna poniżej -10°C lub powyżej +10°C jest traktowana jako
    granica zakresu, co oznacza, że używa się odpowiedniej stałej wartości
    (temp_min dla temperatur poniżej -10°C, temp_max dla temperatur powyżej +10°C).
    """
    # Ograniczenie temperatury zewnętrznej do zakresu [-10, 10]°C
    clamped_temp = max(-10.0, min(10.0, outdoor_temp))
    
    slope = (temp_max - temp_min) / 20
    intercept = temp_min - slope * (-10)
    target_temp = slope * clamped_temp + intercept
    target_temp = max(20, min(80, target_temp))
    return target_temp


async def async_unload_entry(hass: HomeAssistant, entry: EcoalConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
