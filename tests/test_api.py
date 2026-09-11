"""Unit tests for eCoal XML parser and API client."""

import unittest

from custom_components.ecoal.api import (
    EcoalApiError,
    EcoalClient,
    parse_registers_xml,
)

SAMPLE_VALID_XML = """
<cmd status="ok">
  <device id="0">
    <reg vid="0" tid="t1_value" v="31.04" min="-50.00" max="120.00"/>
    <reg vid="0" tid="fuel_level" v="88" min="0" max="100"/>
    <reg vid="0" tid="next_fuel_time" v="1789998790"/>
    <reg vid="0" tid="out_zaw4d" v="0" min="0" max="2"/>
    <reg vid="0" tid="tryb_auto_state" v="1" min="0" max="2"/>
    <reg vid="0" tid="tcwu_value" v="55.16" min="-50.00" max="120.00"/>
    <reg vid="0" tid="tkot_value" v="59.45" min="-50.00" max="120.00"/>
    <reg vid="0" tid="tsp_value" v="53.76" min="-50.00" max="600.00"/>
    <reg vid="0" tid="t2_value" status="outdated_data"/>
    <reg vid="0" tid="out_pomp1" v="0" min="0" max="1"/>
    <reg vid="0" tid="out_cwu" v="0" min="0" max="1"/>
    <reg vid="0" tid="tpow_value" v="56.58" min="-50.00" max="120.00"/>
    <reg vid="0" tid="ob1_zaw4d_pos" v="0" min="0" max="100"/>
    <reg vid="0" tid="kot_tzad" v="55" min="42" max="80"/>
    <reg vid="0" tid="kot_status" v="2" min="0" max="2"/>
    <reg vid="0" tid="ob1_zaw4d_tzad" v="40" min="20" max="80"/>
    <reg vid="0" tid="cwu_tzad" v="55" min="20" max="60"/>
    <reg vid="0" tid="out_dm" v="0" min="0" max="1"/>
    <reg vid="0" tid="zima_lato" v="1" min="0" max="2"/>
    <reg vid="0" tid="zima_lato_state" v="1" min="0" max="1"/>
  </device>
</cmd>
"""

SAMPLE_ERROR_STATUS_XML = """
<cmd status="error">
  <error code="1" message="Invalid device"/>
</cmd>
"""

SAMPLE_MALFORMED_XML = "<cmd status='ok'><device id='0'><reg></device>"


class TestEcoalParser(unittest.TestCase):
    """Test suite for eCoal XML parser and client helper logic."""

    def test_parse_registers_valid_xml(self) -> None:
        """Test parsing a valid eCoal XML response."""
        registers = parse_registers_xml(SAMPLE_VALID_XML)

        self.assertIsInstance(registers, dict)
        self.assertEqual(registers["tkot_value"], "59.45")
        self.assertEqual(registers["tcwu_value"], "55.16")
        self.assertEqual(registers["fuel_level"], "88")
        self.assertEqual(registers["next_fuel_time"], "1789998790")
        self.assertEqual(registers["tryb_auto_state"], "1")
        self.assertEqual(registers["zima_lato"], "1")
        self.assertEqual(registers["zima_lato_state"], "1")
        self.assertEqual(registers["kot_tzad"], "55")
        self.assertEqual(registers["kot_status"], "2")
        self.assertEqual(registers["ob1_zaw4d_tzad"], "40")
        self.assertEqual(registers["cwu_tzad"], "55")
        self.assertEqual(registers["out_pomp1"], "0")

    def test_parse_registers_omits_missing_v(self) -> None:
        """Test that registers without 'v' attribute (like outdated_data) are omitted."""
        registers = parse_registers_xml(SAMPLE_VALID_XML)

        # t2_value only has status="outdated_data" and no 'v' attribute
        self.assertNotIn("t2_value", registers)

    def test_parse_registers_status_error(self) -> None:
        """Test that XML with status != 'ok' raises EcoalApiError."""
        with self.assertRaises(EcoalApiError):
            parse_registers_xml(SAMPLE_ERROR_STATUS_XML)

    def test_parse_registers_malformed_xml(self) -> None:
        """Test that malformed XML raises EcoalApiError."""
        with self.assertRaises(EcoalApiError):
            parse_registers_xml(SAMPLE_MALFORMED_XML)

    def test_client_host_sanitization(self) -> None:
        """Test that host is sanitized properly without protocol and trailing slashes."""
        client1 = EcoalClient(
            host="http://192.168.1.50/",
            username="admin",
            password="secret",
            session=None,
        )
        self.assertEqual(client1.host, "192.168.1.50")
        self.assertEqual(client1._url, "http://192.168.1.50/getregister.cgi")

        client2 = EcoalClient(
            host="https://ecoal.local:8080",
            username="admin",
            password="secret",
            session=None,
        )
        self.assertEqual(client2.host, "ecoal.local:8080")
        self.assertEqual(client2._url, "http://ecoal.local:8080/getregister.cgi")


if __name__ == "__main__":
    unittest.main()
