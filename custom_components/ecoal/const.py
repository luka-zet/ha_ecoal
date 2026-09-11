"""Constants for the eCoal integration."""

from datetime import timedelta
import logging

DOMAIN = "ecoal"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

DEFAULT_PORT = 80

DEFAULT_SCAN_INTERVAL = timedelta(seconds=15)
DEFAULT_TIMEOUT = 10

# Opcje konfiguracyjne dla trybu Auto Zima/Lato
CONF_EXT_TEMP_SENSOR = "ext_temp_sensor"

LOGGER = logging.getLogger(__package__)

# List of registers queried from the eCoal controller
REGISTER_LIST: tuple[str, ...] = (
    "t1_value",
    "fuel_level",
    "next_fuel_time",
    "out_zaw4d",
    "tryb_auto_state",
    "tcwu_value",
    "tkot_value",
    "tsp_value",
    "out_pomp1",
    "out_cwu",
    "tpow_value",
    "ob1_zaw4d_pos",
    "kot_tzad",
    "ob1_zaw4d_tzad",
    "cwu_tzad",
    "out_dm",
    "zima_lato",
    "zima_lato_state",
)
