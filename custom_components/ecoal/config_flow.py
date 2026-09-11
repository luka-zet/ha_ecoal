"""Config flow for eCoal integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EcoalApiError, EcoalAuthError, EcoalClient, EcoalConnectionError
from .const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    CONF_EXT_TEMP_SENSOR,
    DEFAULT_PORT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class EcoalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for eCoal."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return EcoalOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            raw_host = user_input[CONF_HOST].strip()
            clean_host = (
                raw_host.removeprefix("http://").removeprefix("https://").rstrip("/")
            )
            # Normalize port (default when not provided)
            port = int(user_input.get(CONF_PORT, DEFAULT_PORT))
            user_input[CONF_HOST] = clean_host
            user_input[CONF_PORT] = port

            await self.async_set_unique_id(clean_host.lower())
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            client = EcoalClient(
                host=clean_host,
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                session=session,
                port=port,
            )

            try:
                await client.async_get_registers()
            except EcoalAuthError:
                errors["base"] = "invalid_auth"
            except (EcoalConnectionError, EcoalApiError):
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception during eCoal configuration")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"eCoal ({clean_host}:{port})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class EcoalOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for eCoal integration."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        ext_temp_sensor = options.get(CONF_EXT_TEMP_SENSOR)

        schema_dict: dict[Any, Any] = {}

        if ext_temp_sensor:
            schema_dict[vol.Optional(CONF_EXT_TEMP_SENSOR, default=ext_temp_sensor)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
            )
        else:
            schema_dict[vol.Optional(CONF_EXT_TEMP_SENSOR)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
        )
