"""API client for the eCoal boiler controller."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
import xml.etree.ElementTree as ET

try:
    import aiohttp
    import yarl
except ImportError:  # pragma: no cover
    aiohttp = None  # type: ignore[assignment]
    yarl = None  # type: ignore[assignment]

from .const import DEFAULT_PORT, DEFAULT_TIMEOUT, LOGGER, REGISTER_LIST


class EcoalApiError(Exception):
    """Base exception for eCoal API errors."""


class EcoalAuthError(EcoalApiError):
    """Exception raised when authentication fails."""


class EcoalConnectionError(EcoalApiError):
    """Exception raised when connection to the controller fails."""


def parse_registers_xml(xml_content: str) -> dict[str, str]:
    """Parse XML response from eCoal controller and extract registers.

    Maps elements by `tid` attribute and ignores registers without `v` attribute.
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as err:
        raise EcoalApiError(f"Failed to parse XML response: {err}") from err

    if root.tag != "cmd" or root.attrib.get("status") != "ok":
        status = root.attrib.get("status", "unknown")
        raise EcoalApiError(f"Invalid API response status: {status}")

    registers: dict[str, str] = {}
    for reg in root.iter("reg"):
        tid = reg.attrib.get("tid")
        value = reg.attrib.get("v")
        if tid and value is not None:
            registers[tid] = value

    return registers


class EcoalClient:
    """Async client for communicating with the eCoal controller."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession | Any,
        port: int = DEFAULT_PORT,
    ) -> None:
        """Initialize the eCoal API client."""
        # Strip protocol and trailing slashes if accidentally provided
        clean_host = host.removeprefix("http://").removeprefix("https://").rstrip("/")
        self.host = clean_host
        self._port = int(port)
        self._username = username
        self._password = password
        self._session = session
        self._url = f"http://{self.host}:{self._port}/getregister.cgi"

    @property
    def port(self) -> int:
        """Return the configured port."""
        return self._port

    @property
    def base_url(self) -> str:
        """Return the base URL of the controller (without path)."""
        return f"http://{self.host}:{self._port}"

    async def async_get_registers(self) -> dict[str, str]:
        """Fetch and parse registers from the controller."""
        if aiohttp is None:
            raise EcoalApiError("aiohttp is required to fetch registers")

        # Build exact query string: device=0&reg1&reg2...
        query_string = "device=0&" + "&".join(REGISTER_LIST)
        full_url_str = f"{self._url}?{query_string}"

        # Use yarl.URL with encoded=True so aiohttp doesn't parse query params and add '='
        if yarl is not None:
            request_url = yarl.URL(full_url_str, encoded=True)
        else:
            request_url = full_url_str  # type: ignore[assignment]

        auth = aiohttp.BasicAuth(self._username, self._password)
        timeout = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug("Fetching eCoal data from %s", full_url_str)

        try:
            async with self._session.get(
                request_url,
                auth=auth,
                timeout=timeout,
            ) as response:
                if response.status == 401:
                    raise EcoalAuthError("Authentication failed: invalid credentials")
                if response.status != 200:
                    raise EcoalApiError(
                        f"Unexpected HTTP status code from controller: {response.status}"
                    )

                text = await response.text()
                if LOGGER.isEnabledFor(logging.DEBUG):
                    LOGGER.debug("Received XML response from eCoal (%s):\n%s", self.host, text)

        except EcoalApiError:
            raise
        except (asyncio.TimeoutError, TimeoutError) as err:
            raise EcoalConnectionError(
                f"Timeout connecting to eCoal controller at {self.host}"
            ) from err
        except aiohttp.ClientError as err:
            raise EcoalConnectionError(
                f"Error connecting to eCoal controller at {self.host}: {err}"
            ) from err
        except Exception as err:
            raise EcoalApiError(
                f"Unexpected error communicating with eCoal controller: {err}"
            ) from err

        return parse_registers_xml(text)

    async def async_set_register(self, write_register: str, value: Any) -> None:
        """Set a register value on the eCoal controller."""
        if aiohttp is None:
            raise EcoalApiError("aiohttp is required to communicate")

        # The eCoal controller uses a specific query format for writing: 0@reg=val
        query_string = f"0@{write_register}={value}"
        full_url = f"{self.base_url}/setregister.cgi?{query_string}"

        auth = aiohttp.BasicAuth(self._username, self._password)
        timeout = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug("Setting eCoal register on %s: %s", self.host, query_string)

        try:
            async with self._session.get(
                full_url,
                auth=auth,
                timeout=timeout,
            ) as response:
                if response.status == 401:
                    raise EcoalAuthError("Authentication failed: invalid credentials")
                if response.status != 200:
                    raise EcoalApiError(
                        f"Unexpected HTTP status code from controller: {response.status}"
                    )

                text = await response.text()
                if LOGGER.isEnabledFor(logging.DEBUG):
                    LOGGER.debug("Received set response from eCoal (%s):\n%s", self.host, text)

                # eCoal setregister.cgi usually returns an XML <cmd status="ok"> as well
                try:
                    root = ET.fromstring(text)
                    if root.tag != "cmd" or root.attrib.get("status") != "ok":
                        LOGGER.warning("Set command might have failed: %s", text)
                except ET.ParseError:
                    pass # ignore if not XML

        except (asyncio.TimeoutError, TimeoutError) as err:
            raise EcoalConnectionError(
                f"Timeout setting register on eCoal controller at {self.host}"
            ) from err
        except aiohttp.ClientError as err:
            raise EcoalConnectionError(
                f"Error setting register on eCoal controller at {self.host}: {err}"
            ) from err
        except EcoalApiError:
            raise
        except Exception as err:
            raise EcoalApiError(
                f"Unexpected error setting register on eCoal controller: {err}"
            ) from err
