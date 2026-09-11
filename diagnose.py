import sys
import xml.etree.ElementTree as ET

# Ensure custom_components is in the path
sys.path.insert(0, ".")

try:
    from custom_components.ecoal.api import parse_registers_xml, EcoalClient
    from custom_components.ecoal.const import REGISTER_LIST
    from custom_components.ecoal.sensor import SENSOR_DESCRIPTIONS
    from custom_components.ecoal.number import NUMBER_DESCRIPTIONS
    from custom_components.ecoal.select import SELECT_DESCRIPTIONS
    print("Successfully imported all components!")
except Exception as err:
    print(f"IMPORT ERROR: {err}")
    sys.exit(1)

XML_DATA = """<cmd status="ok">
<device id="0">
<reg vid="0" tid="t1_value" v="31.12" min="-50.00" max="120.00"/>
<reg vid="0" tid="fuel_level" v="83" min="0" max="100"/>
<reg vid="0" tid="next_fuel_time" v="1789976032"/>
<reg vid="0" tid="out_zaw4d" v="0" min="0" max="2"/>
<reg vid="0" tid="tryb_auto_state" v="1" min="0" max="2"/>
<reg vid="0" tid="tcwu_value" v="50.20" min="-50.00" max="120.00"/>
<reg vid="0" tid="tkot_value" v="65.45" min="-50.00" max="120.00"/>
<reg vid="0" tid="tsp_value" v="56.12" min="-50.00" max="600.00"/>
<reg vid="0" tid="t2_value" status="outdated_data"/>
<reg vid="0" tid="out_pomp1" v="0" min="0" max="1"/>
<reg vid="0" tid="out_cwu" v="1" min="0" max="1"/>
<reg vid="0" tid="tpow_value" v="59.37" min="-50.00" max="120.00"/>
<reg vid="0" tid="ob1_zaw4d_pos" v="0" min="0" max="100"/>
<reg vid="0" tid="kot_tzad" v="55" min="42" max="80"/>
<reg vid="0" tid="ob1_zaw4d_tzad" v="40" min="20" max="80"/>
<reg vid="0" tid="cwu_tzad" v="55" min="20" max="60"/>
<reg vid="0" tid="out_dm" v="0" min="0" max="1"/>
<reg vid="0" tid="zima_lato" v="1" min="0" max="2"/>
<reg vid="0" tid="zima_lato_state" v="1" min="0" max="1"/>
</device>
</cmd>"""

try:
    data = parse_registers_xml(XML_DATA)
    print("\nParsed XML successfully! Extracted keys:")
    print(list(data.keys()))
    
    print("\nChecking Sensor descriptions:")
    for desc in SENSOR_DESCRIPTIONS:
        val = desc.value_fn(data)
        print(f"  Sensor '{desc.name}' ({desc.key}) -> {val}")

    print("\nChecking Number descriptions:")
    for desc in NUMBER_DESCRIPTIONS:
        val = desc.value_fn(data)
        print(f"  Number '{desc.name}' ({desc.key}) -> {val}")

    print("\nChecking Select descriptions:")
    for desc in SELECT_DESCRIPTIONS:
        val = desc.value_fn(data)
        print(f"  Select '{desc.name}' ({desc.key}) -> {val}")

except Exception as err:
    print(f"RUNTIME RUN ERROR: {err}")
    sys.exit(1)
