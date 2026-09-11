"""DataUpdateCoordinator for the eCoal integration."""

from __future__ import annotations

import logging
from typing import Any, Generic, TypeVar

try:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.update_coordinator import (
        DataUpdateCoordinator,
        UpdateFailed,
    )
except ImportError:  # pragma: no cover
    _DataT = TypeVar("_DataT")
    HomeAssistant = None  # type: ignore[assignment, misc]

    class UpdateFailed(Exception):  # type: ignore[no-redef]
        """Fallback UpdateFailed exception when homeassistant is not installed."""

    class DataUpdateCoordinator(Generic[_DataT]):  # type: ignore[no-redef]
        """Fallback DataUpdateCoordinator when homeassistant is not installed."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass


from .api import EcoalApiError, EcoalClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class EcoalDataUpdateCoordinator(DataUpdateCoordinator[dict[str, str]]):
    """Class to manage fetching eCoal boiler data."""

    def __init__(self, hass: HomeAssistant, client: EcoalClient) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
            always_update=False,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, str]:
        """Fetch data from eCoal controller."""
        try:
            return await self.client.async_get_registers()
        except EcoalApiError as err:
            raise UpdateFailed(
                f"Error fetching data from eCoal controller: {err}"
            ) from err
