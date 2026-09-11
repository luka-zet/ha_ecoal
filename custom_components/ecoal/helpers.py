"""Helper utilities for the eCoal integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)


# ============================================================
# Parsowanie wartości z rejestrów
# ============================================================

def parse_float(data: Dict[str, str], key: str) -> Optional[float]:
    """Safely extract and convert register value to float.
    
    Returns None if the key is missing or value cannot be converted.
    """
    raw_val = data.get(key)
    if raw_val is None:
        return None
    try:
        return float(raw_val)
    except (ValueError, TypeError):
        return None


def parse_int(data: Dict[str, str], key: str) -> Optional[int]:
    """Safely extract and convert register value to int."""
    raw_val = data.get(key)
    if raw_val is None:
        return None
    try:
        return int(float(raw_val))
    except (ValueError, TypeError):
        return None


from datetime import datetime, timezone

def parse_timestamp(data: Dict[str, str], key: str) -> Optional[datetime]:
    """Parse Unix timestamp from register into timezone-aware datetime.
    
    Returns None for missing, invalid, or non-positive timestamps.
    """
    raw_val = data.get(key)
    if raw_val is None:
        return None
    try:
        # Convert to float first, then check if it's a valid timestamp
        ts = float(raw_val)
        
        # Check for valid timestamp range (Unix timestamps are positive)
        if ts <= 0:
            return None
            
        # If it's 13+ digits, treat it as milliseconds (common for modern devices)
        if ts >= 1000000000000:  # 13 digits
            ts = ts / 1000.0
            
        # Check against maximum reasonable Unix timestamp
        if ts > 253402300799:  # 2099-12-31 UTC 
            return None
            
        # Create timezone-aware datetime
        return datetime.fromtimestamp(ts, tz=timezone.utc)
        
    except (ValueError, TypeError, OverflowError, OSError) as err:
        # Work around rare parsing failures but don't crash
        return None




def parse_bool_running(data: Dict[str, str], key: str) -> Optional[bool]:
    """Check if an output register is active (value > 0).
    
    Returns None for missing or unparseable values.
    """
    raw_val = data.get(key)
    if raw_val is None:
        return None
    try:
        return float(raw_val) > 0
    except (ValueError, TypeError):
        return None


# ============================================================
# Mapowanie wartości specyficznych dla kotła
# ============================================================

def parse_zima_lato(data: Dict[str, str]) -> Optional[str]:
    """Map summer/winter mode (0: Zima, 1: Lato, 2: Auto)."""
    raw_val = data.get("zima_lato")
    if raw_val is None:
        return None
    return {
        "0": "Zima",
        "1": "Lato",
        "2": "Auto zima/lato",
    }.get(raw_val, f"Nieznany ({raw_val})")


def parse_tryb_auto(data: Dict[str, str]) -> Optional[str]:
    """Map boiler auto state (0: Ręczny, 1: Automatyczny, 2: Alarmowy)."""
    raw_val = data.get("tryb_auto_state")
    if raw_val is None:
        return None
    return {
        "0": "Ręczny",
        "1": "Automatyczny",
        "2": "Alarmowy",
    }.get(raw_val, f"Nieznany ({raw_val})")


def parse_kot_status(data: Dict[str, str]) -> Optional[str]:
    """Map boiler work status (0: Stop, 1: Podtrzymanie, 2: Grzanie)."""
    raw_val = data.get("kot_status")
    if raw_val is None:
        return None
    return {
        "0": "Stop",
        "1": "Podtrzymanie",
        "2": "Grzanie",
    }.get(raw_val, f"Nieznany ({raw_val})")


# ============================================================
# Walidacja wartości
# ============================================================

def clamp(value: float, min_val: float, max_val: float) -> float:
    """Constrain value to be within [min_val, max_val]."""
    return max(min_val, min(max_val, value))


def safe_float_conversion(value: float) -> str:
    """Convert float to string, using int if value has no fractional part.
    
    This is used for sending values to the boiler controller.
    """
    return str(int(value)) if value == int(value) else str(value)


# ============================================================
# Helpers dla state management
# ============================================================

def is_state_valid(state: Any) -> bool:
    """Check if a Home Assistant state is valid (not unknown/unavailable)."""
    if state is None:
        return False
    return state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)


def safe_state_to_float(state: Any) -> Optional[float]:
    """Safely convert a HA state to float.
    
    Returns None for missing, unavailable, or unparseable states.
    """
    if not is_state_valid(state):
        return None
    try:
        return float(state.state)
    except (ValueError, TypeError):
        return None