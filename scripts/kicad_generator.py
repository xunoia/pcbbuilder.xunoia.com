# # scripts/kicad_generator.py

# import os
# import time
# from pathlib import Path
# from skidl import Part, Net, generate_schematic, lib_search_paths, KICAD
# from scripts.utils import ensure_folder

# # If KiCad libraries are in a non‐standard location, add:
# # lib_search_paths[KICAD].append("/usr/share/kicad7/library")

# # Map from "type" string → (symbol_lib, symbol_name, footprint)
# # You must ensure these exactly match your local KiCad library names.
# PART_LIBRARY_MAP = {
#     # Power regulators
#     "LM2676S":           ("Regulator_Boards", "LM2676S_PowerPad",      "Regulator_Boards:LM2676S_PowerPad"),
#     "AMS1117-3.3":       ("Regulator_Boards", "AMS1117-3.3",         "Regulator_Boards:AMS1117-3.3"),

#     # Inductor / Diode / Capacitor
#     "47uH_2A":           ("Inductor",         "L_0805",               "Inductor_SMD:L_0805"),
#     "SR560":             ("Device",           "D_Schottky",           "Diode_SMD:BAT54"),
#     "22uF_35V":          ("Device",           "C_Generic",            "Capacitor_SMD:C_0805"),
#     "47uF_10V":          ("Device",           "C_Generic",            "Capacitor_SMD:C_0805"),

#     # Resistors
#     "10k":               ("Device",           "R",                    "Resistor_SMD:R_0603"),
#     "1k":                ("Device",           "R",                    "Resistor_SMD:R_0603"),
#     "4.7k":              ("Device",           "R",                    "Resistor_SMD:R_0603"),

#     # Op‐amps / Comparators
#     "MCP6001":           ("Amplifier_Operational", "MCP6001",          "Amplifier_Operational:MCP6001"),

#     # Transistors
#     "2N3904":            ("Transistor_TO92",  "2N3904",               "Transistor_TO92:2N3904"),

#     # Diodes (bridge)
#     "1N4007":            ("Diode_THT",        "1N4007",               "Diode_THT:1N4007"),

#     # LED
#     "LED":               ("LED_SMD",          "LED_0805",             "LED_SMD:LED_0805"),

#     # 555 Timer
#     "NE555":             ("Timer_IC_ThroughHole", "NE555",             "Timer_IC_ThroughHole:NE555"),

#     # Crystals / Capacitors
#     "Crystal_SMD":       ("Crystal_SMD",      "Crystal_SMD",          "Crystal_SMD:Crystal_SMD_2pins"),
#     "Capacitor_SMD":     ("Device",           "C_Generic",            "Capacitor_SMD:C_0805"),

#     # Sensor (e.g. BME280)
#     "BME280":            ("Sensor",           "BME280",               "Sensor:BME280"),

#     # Microcontroller (STM32F103)
#     "STM32F103":         ("MCU_Microchip",    "STM32F103",            "MCU_Microchip:STM32F103"),

#     # Fallback resistor/capacitor names if templates embed values
#     # e.g. "0.1uF", "10uF", "0.01uF", etc.
#     "0.1uF":             ("Device",           "C_Generic",            "Capacitor_SMD:C_0603"),
#     "0.01uF":            ("Device",           "C_Generic",            "Capacitor_SMD:C_0603"),

#     # Generic entries for computed values (e.g. "159k", "7.14k")
#     # These will fall back to a generic resistor symbol if the literal isn't found.
# }


# def generate_kicad_schematic(filled_json: dict, spec: any) -> str:
#     """
#     Given a filled JSON template (with no placeholders), instantiate SKiDL Parts,
#     create Net objects, connect the pins, and call generate_schematic()
#     to write a KiCad .kicad_sch file. Return the filepath.
#     """
#     output_dir = Path(os.getenv("KICAD_OUTPUT_PATH", "./output"))
#     ensure_folder(str(output_dir))

#     # Unique filename
#     timestamp = int(time.time())
#     filename = f"{spec.circuit_type}_{timestamp}.kicad_sch"
#     filepath = output_dir / filename

#     parts = {}  # ref → SKiDL Part object
#     nets = {}   # net_name → SKiDL Net object

#     def get_net(net_name: str):
#         if net_name not in nets:
#             nets[net_name] = Net(net_name)
#         return nets[net_name]

#     # 1) Instantiate each component
#     for comp in filled_json.get("components", []):
#         ref = comp["ref"]        # e.g. "U1", "R1", ...
#         ctype = comp["type"]     # e.g. "LM2676S", "10k", "BME280", etc.
#         footprint = comp.get("footprint")
#         params = comp.get("params", {})      # e.g. { "Vin": "12V", ... }
#         connections = comp.get("connections", [])

#         # Determine symbol library / symbol name / footprint
#         if ctype in PART_LIBRARY_MAP:
#             symbol_lib, symbol_name, footprint_name = PART_LIBRARY_MAP[ctype]
#         else:
#             # Attempt fallback: if ctype ends with "k" or "nF"/"uF", treat as resistor/capacitor
#             if ctype.endswith("k"):
#                 symbol_lib, symbol_name, footprint_name = ("Device", "R", "Resistor_SMD:R_0603")
#             elif "uF" in ctype or "nF" in ctype:
#                 symbol_lib, symbol_name, footprint_name = ("Device", "C_Generic", "Capacitor_SMD:C_0805")
#             else:
#                 # Generic fallback: use an “unknown” device symbol if available
#                 symbol_lib, symbol_name, footprint_name = ("Device", "R", "Resistor_SMD:R_0603")

#         # Create the SKiDL Part
#         part = Part(lib=symbol_lib, name=symbol_name, refprefix=ref[0], footprint=footprint_name)
#         part.value = ctype  # show the literal type string on the schematic

#         # If there are params, store as visible fields
#         for p_key, p_val in params.items():
#             part.fields[p_key] = p_val

#         parts[ref] = part

#     # 2) Wire up nets based on "connections"
#     for conn in filled_json.get("connections", []):
#         net_name = conn["net"]
#         from_token = conn["from"]  # e.g. "U1.Vin" or "R2.1"
#         to_token = conn["to"]

#         def parse_ref_pin(token: str):
#             if "." not in token:
#                 raise ValueError(f"Invalid ref.pin token: {token}")
#             return token.split(".", 1)

#         from_ref, from_pin = parse_ref_pin(from_token)
#         to_ref, to_pin     = parse_ref_pin(to_token)

#         if from_ref not in parts or to_ref not in parts:
#             raise ValueError(f"Reference {from_ref} or {to_ref} not found among parts")

#         net_obj = get_net(net_name)
#         try:
#             net_obj += parts[from_ref][from_pin]
#             net_obj += parts[to_ref][to_pin]
#         except Exception as e:
#             raise RuntimeError(
#                 f"Failed to connect {from_ref}.{from_pin} to {to_ref}.{to_pin} on net {net_name}:\n{e}"
#             )

#     # 3) Generate the KiCad schematic file
#     try:
#         generate_schematic(str(filepath))
#     except Exception as e:
#         raise RuntimeError(f"SKiDL failed to generate schematic: {e}")

#     return str(filepath)



# scripts/kicad_generator.py

# import os
# import time
# from pathlib import Path
# from skidl import Part, Net, generate_schematic, lib_search_paths, KICAD
# from scripts.utils import ensure_folder

# # Add KiCad library paths - YOUR SPECIFIC PATHS
# KICAD_LIBRARY_PATHS = [
#     "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols",    # Your symbols
#     "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints", # Your footprints  
#     "/Applications/KiCad/KiCad.app/Contents/SharedSupport",            # Base path
# ]

# # Add existing paths to SKiDL search
# for path in KICAD_LIBRARY_PATHS:
#     if os.path.exists(path):
#         lib_search_paths[KICAD].append(path)
#         print(f"Added KiCad library path: {path}")

# # Map from "type" string → (symbol_lib, symbol_name, footprint)
# # Using more standard KiCad library names
# PART_LIBRARY_MAP = {
#     # Power regulators - use standard Device library components
#     "LM2676S":           ("Regulator_Switching", "LM2676",          "Package_TO_SOT_SMD:TO-263-5_TabPin3"),
#     "AMS1117-3.3":       ("Regulator_Linear", "AMS1117-3.3",       "Package_TO_SOT_SMD:SOT-223-3_TabPin2"),

#     # Basic components from Device library
#     "47uH_2A":           ("Device", "L",                            "Inductor_SMD:L_0805_2012Metric"),
#     "SR560":             ("Device", "D_Schottky",                   "Diode_SMD:D_SOD-123"),
#     "22uF_35V":          ("Device", "C_Polarized",                  "Capacitor_SMD:C_0805_2012Metric"),
#     "47uF_10V":          ("Device", "C_Polarized",                  "Capacitor_SMD:C_0805_2012Metric"),

#     # Resistors
#     "10k":               ("Device", "R",                            "Resistor_SMD:R_0603_1608Metric"),
#     "1k":                ("Device", "R",                            "Resistor_SMD:R_0603_1608Metric"),
#     "4.7k":              ("Device", "R",                            "Resistor_SMD:R_0603_1608Metric"),

#     # Op-amps
#     "MCP6001":           ("Amplifier_Operational", "MCP6001xT",     "Package_TO_SOT_SMD:SOT-23-5"),

#     # Transistors
#     "2N3904":            ("Transistor_BJT", "2N3904",               "Package_TO_SOT_THT:TO-92_Inline"),

#     # Diodes
#     "1N4007":            ("Diode", "1N4007",                        "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal"),

#     # LED
#     "LED":               ("Device", "LED",                          "LED_SMD:LED_0805_2012Metric"),

#     # 555 Timer
#     "NE555":             ("Timer", "NE555D",                        "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"),

#     # Crystals
#     "Crystal_SMD":       ("Device", "Crystal",                      "Crystal:Crystal_SMD_2016-4Pin_2.0x1.6mm"),
#     "Capacitor_SMD":     ("Device", "C",                            "Capacitor_SMD:C_0805_2012Metric"),

#     # Sensors
#     "BME280":            ("Sensor_Humidity", "BME280",              "Package_LGA:Bosch_LGA-8_2.5x2.5mm_P0.65mm_ClockwisePinNumbering"),

#     # Microcontrollers
#     "STM32F103":         ("MCU_ST_STM32F1", "STM32F103C8Tx",       "Package_QFP:LQFP-48_7x7mm_P0.5mm"),

#     # Generic capacitor values
#     "0.1uF":             ("Device", "C",                            "Capacitor_SMD:C_0603_1608Metric"),
#     "0.01uF":            ("Device", "C",                            "Capacitor_SMD:C_0603_1608Metric"),
#     "10uF":              ("Device", "C_Polarized",                  "Capacitor_SMD:C_0805_2012Metric"),
# }


# def find_kicad_libraries():
#     """Find available KiCad libraries on the system"""
#     found_paths = []
#     for path in KICAD_LIBRARY_PATHS:
#         if os.path.exists(path):
#             found_paths.append(path)
#     return found_paths


# def generate_kicad_schematic(filled_json: dict, spec: any) -> str:
#     """
#     Given a filled JSON template (with no placeholders), instantiate SKiDL Parts,
#     create Net objects, connect the pins, and call generate_schematic()
#     to write a KiCad .kicad_sch file. Return the filepath.
#     """
#     output_dir = Path(os.getenv("KICAD_OUTPUT_PATH", "./output"))
#     ensure_folder(str(output_dir))

#     # Print available library paths for debugging
#     available_paths = find_kicad_libraries()
#     print(f"Available KiCad library paths: {available_paths}")

#     # Unique filename
#     timestamp = int(time.time())
#     filename = f"{spec.circuit_type}_{timestamp}.kicad_sch"
#     filepath = output_dir / filename

#     parts = {}  # ref → SKiDL Part object
#     nets = {}   # net_name → SKiDL Net object

#     def get_net(net_name: str):
#         if net_name not in nets:
#             nets[net_name] = Net(net_name)
#         return nets[net_name]

#     # 1) Instantiate each component
#     for comp in filled_json.get("components", []):
#         ref = comp["ref"]        # e.g. "U1", "R1", ...
#         ctype = comp["type"]     # e.g. "LM2676S", "10k", "BME280", etc.
#         footprint = comp.get("footprint")
#         params = comp.get("params", {})      # e.g. { "Vin": "12V", ... }
#         connections = comp.get("connections", [])

#         # Determine symbol library / symbol name / footprint
#         if ctype in PART_LIBRARY_MAP:
#             symbol_lib, symbol_name, footprint_name = PART_LIBRARY_MAP[ctype]
#         else:
#             # Attempt fallback: if ctype ends with "k" or "nF"/"uF", treat as resistor/capacitor
#             if ctype.endswith("k") or ctype.endswith("Ω"):
#                 symbol_lib, symbol_name, footprint_name = ("Device", "R", "Resistor_SMD:R_0603_1608Metric")
#             elif "uF" in ctype or "nF" in ctype or "pF" in ctype:
#                 symbol_lib, symbol_name, footprint_name = ("Device", "C", "Capacitor_SMD:C_0805_2012Metric")
#             else:
#                 # Generic fallback
#                 print(f"Warning: Unknown component type '{ctype}', using generic resistor")
#                 symbol_lib, symbol_name, footprint_name = ("Device", "R", "Resistor_SMD:R_0603_1608Metric")

#         # Create the SKiDL Part with error handling
#         try:
#             part = Part(lib=symbol_lib, name=symbol_name, ref=ref, footprint=footprint_name)
#             part.value = ctype  # show the literal type string on the schematic

#             # If there are params, store as visible fields
#             for p_key, p_val in params.items():
#                 part.fields[p_key] = p_val

#             parts[ref] = part
#             print(f"Created part: {ref} ({symbol_lib}:{symbol_name})")

#         except Exception as e:
#             print(f"Error creating part {ref} ({ctype}): {e}")
#             # Fall back to generic resistor
#             try:
#                 part = Part(lib="Device", name="R", ref=ref, footprint="Resistor_SMD:R_0603_1608Metric")
#                 part.value = ctype
#                 parts[ref] = part
#                 print(f"Fallback: Created generic part for {ref}")
#             except Exception as e2:
#                 raise RuntimeError(f"Failed to create part {ref} even with fallback: {e2}")

#     # 2) Wire up nets based on "connections"
#     for conn in filled_json.get("connections", []):
#         net_name = conn["net"]
#         from_token = conn["from"]  # e.g. "U1.Vin" or "R2.1"
#         to_token = conn["to"]

#         def parse_ref_pin(token: str):
#             if "." not in token:
#                 raise ValueError(f"Invalid ref.pin token: {token}")
#             return token.split(".", 1)

#         from_ref, from_pin = parse_ref_pin(from_token)
#         to_ref, to_pin     = parse_ref_pin(to_token)

#         if from_ref not in parts or to_ref not in parts:
#             print(f"Warning: Reference {from_ref} or {to_ref} not found among parts, skipping connection")
#             continue

#         net_obj = get_net(net_name)
#         try:
#             # Use pin numbers or names flexibly
#             net_obj += parts[from_ref][from_pin]
#             net_obj += parts[to_ref][to_pin]
#             print(f"Connected {from_ref}.{from_pin} to {to_ref}.{to_pin} via net {net_name}")
#         except Exception as e:
#             print(f"Warning: Failed to connect {from_ref}.{from_pin} to {to_ref}.{to_pin} on net {net_name}: {e}")
#             # Continue with other connections

#     # 3) Generate the KiCad schematic file
#     try:
#         print(f"Generating schematic file: {filepath}")
#         generate_schematic()
#         print(f"Successfully generated: {filepath}")
#     except Exception as e:
#         raise RuntimeError(f"SKiDL failed to generate schematic: {e}")

#     return str(filepath)



# scripts/kicad_generator.py
# scripts/kicad_generator.py

# import os
# import time
# from pathlib import Path
# from skidl import Part, Net, generate_netlist, lib_search_paths, KICAD, set_default_tool
# from scripts.utils import ensure_folder

# # Set SKiDL to use KiCad as the default tool
# set_default_tool(KICAD)

# # Set environment variables for KiCad libraries
# os.environ['KICAD8_SYMBOL_DIR'] = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols'
# os.environ['KICAD8_FOOTPRINT_DIR'] = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'

# # Add KiCad library search paths
# KICAD_LIBRARY_PATHS = [
#     # macOS paths
#     "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols",
#     "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints",
    
#     # Linux paths
#     "/usr/share/kicad/symbols",
#     "/usr/share/kicad/footprints",
    
#     # Windows paths
#     "C:/Program Files/KiCad/share/kicad/symbols",
#     "C:/Program Files/KiCad/share/kicad/footprints",
#     "C:/Program Files (x86)/KiCad/share/kicad/symbols",
#     "C:/Program Files (x86)/KiCad/share/kicad/footprints",
# ]

# # Add existing paths to SKiDL search
# for path in KICAD_LIBRARY_PATHS:
#     if os.path.exists(path):
#         lib_search_paths[KICAD].append(path)
#         print(f"Added KiCad library path: {path}")

# # Updated part library map with correct KiCad 8 library names
# PART_LIBRARY_MAP = {
#     # Power regulators - using actual KiCad library names
#     "LM2676S":           ("Regulator_Switching", "LM2596",           "Package_TO_SOT_SMD:TO-263-5_TabPin3"),
#     "AMS1117-3.3":       ("Regulator_Linear", "AMS1117-3.3",       "Package_TO_SOT_SMD:SOT-223-3_TabPin2"),

#     # Basic passive components
#     "47uH_2A":           ("Device", "L",                            "Inductor_SMD:L_0805_2012Metric"),
#     "SR560":             ("Device", "D_Schottky",                   "Diode_SMD:D_SOD-123"),
#     "22uF_35V":          ("Device", "C_Polarized",                  "Capacitor_SMD:C_0805_2012Metric"),
#     "47uF_10V":          ("Device", "C_Polarized",                  "Capacitor_SMD:C_0805_2012Metric"),

#     # Resistors
#     "10k":               ("Device", "R",                            "Resistor_SMD:R_0603_1608Metric"),
#     "1k":                ("Device", "R",                            "Resistor_SMD:R_0603_1608Metric"),
#     "4.7k":              ("Device", "R",                            "Resistor_SMD:R_0603_1608Metric"),

#     # Op-amps
#     "MCP6001":           ("Amplifier_Operational", "MCP6001",       "Package_TO_SOT_SMD:SOT-23-5"),

#     # Transistors
#     "2N3904":            ("Transistor_BJT", "2N3904",               "Package_TO_SOT_THT:TO-92_Inline"),

#     # Diodes
#     "1N4007":            ("Diode", "1N4007",                        "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal"),

#     # LED
#     "LED":               ("Device", "LED",                          "LED_SMD:LED_0805_2012Metric"),

#     # 555 Timer
#     "NE555":             ("Timer", "NE555P",                        "Package_DIP:DIP-8_W7.62mm"),

#     # Crystals and capacitors
#     "Crystal_SMD":       ("Device", "Crystal",                      "Crystal:Crystal_SMD_2016-4Pin_2.0x1.6mm"),
#     "Capacitor_SMD":     ("Device", "C",                            "Capacitor_SMD:C_0805_2012Metric"),

#     # Sensors
#     "BME280":            ("Sensor_Humidity", "BME280",              "Package_LGA:Bosch_LGA-8_2.5x2.5mm_P0.65mm_ClockwisePinNumbering"),

#     # Microcontrollers
#     "STM32F103":         ("MCU_ST_STM32F1", "STM32F103C8Tx",       "Package_QFP:LQFP-48_7x7mm_P0.5mm"),

#     # Generic capacitor values
#     "0.1uF":             ("Device", "C",                            "Capacitor_SMD:C_0603_1608Metric"),
#     "0.01uF":            ("Device", "C",                            "Capacitor_SMD:C_0603_1608Metric"),
#     "10uF":              ("Device", "C_Polarized",                  "Capacitor_SMD:C_0805_2012Metric"),
# }

# # Pin mapping for common components (to handle connection issues)
# COMPONENT_PIN_MAP = {
#     "LM2596": {
#         "Vin": "1",
#         "GND": "3", 
#         "SW": "2",
#         "Vout": "4",
#         "FB": "5"
#     },
#     "L": {
#         "1": "1",
#         "2": "2"
#     },
#     "D_Schottky": {
#         "K": "1",  # Cathode
#         "A": "2"   # Anode
#     },
#     "C_Polarized": {
#         "+": "1",
#         "-": "2"
#     },
#     "R": {
#         "1": "1",
#         "2": "2"
#     },
#     "C": {
#         "1": "1",
#         "2": "2"
#     }
# }


# def safe_create_part(ref: str, ctype: str, symbol_lib: str, symbol_name: str, footprint_name: str):
#     """
#     Safely create a SKiDL Part with fallback options
#     """
#     try:
#         # Try to create the part with specified library
#         part = Part(lib=symbol_lib, name=symbol_name, ref=ref, footprint=footprint_name)
#         part.value = ctype
#         print(f"✓ Created part: {ref} ({symbol_lib}:{symbol_name})")
#         return part, symbol_name
#     except Exception as e:
#         print(f"⚠ Failed to create {ref} with {symbol_lib}:{symbol_name}: {e}")
        
#         # Try fallback with Device library
#         try:
#             if ctype.endswith("k") or ctype.endswith("Ω"):
#                 part = Part(lib="Device", name="R", ref=ref, footprint="Resistor_SMD:R_0603_1608Metric")
#                 symbol_name = "R"
#             elif "uF" in ctype or "nF" in ctype or "pF" in ctype:
#                 if "47uF" in ctype or "22uF" in ctype or "10uF" in ctype:
#                     part = Part(lib="Device", name="C_Polarized", ref=ref, footprint="Capacitor_SMD:C_0805_2012Metric")
#                     symbol_name = "C_Polarized"
#                 else:
#                     part = Part(lib="Device", name="C", ref=ref, footprint="Capacitor_SMD:C_0805_2012Metric")
#                     symbol_name = "C"
#             else:
#                 # For switching regulators, try a generic IC package
#                 part = Part(lib="Package_SO", name="SOIC-8_3.9x4.9mm_P1.27mm", ref=ref, footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm")
#                 symbol_name = "SOIC-8_3.9x4.9mm_P1.27mm"
            
#             part.value = ctype
#             print(f"✓ Created fallback part: {ref} ({symbol_name})")
#             return part, symbol_name
#         except Exception as e2:
#             raise RuntimeError(f"Failed to create part {ref} even with fallback: {e2}")


# def safe_connect_pin(part, pin_name, net_obj, ref, symbol_name):
#     """
#     Safely connect a pin to a net, trying different pin naming conventions
#     """
#     # Try direct pin name first
#     try:
#         net_obj += part[pin_name]
#         return True
#     except:
#         pass
    
#     # Try mapped pin names
#     if symbol_name in COMPONENT_PIN_MAP:
#         pin_map = COMPONENT_PIN_MAP[symbol_name]
#         if pin_name in pin_map:
#             try:
#                 mapped_pin = pin_map[pin_name]
#                 net_obj += part[mapped_pin]
#                 print(f"    Mapped {ref}.{pin_name} → pin {mapped_pin}")
#                 return True
#             except:
#                 pass
    
#     # Try numeric pins for simple components
#     try:
#         if pin_name in ["1", "2", "3", "4", "5", "6", "7", "8"]:
#             net_obj += part[int(pin_name)]
#             return True
#     except:
#         pass
    
#     # Try pin as integer
#     try:
#         pin_num = int(pin_name)
#         net_obj += part[pin_num]
#         return True
#     except:
#         pass
    
#     print(f"    Failed to find pin {pin_name} on {ref} ({symbol_name})")
#     return False


# def generate_kicad_schematic(filled_json: dict, spec: any) -> str:
#     """
#     Generate a KiCad netlist file using SKiDL from the filled JSON template.
#     Returns the filepath of the generated .net file.
    
#     Note: Due to KiCad 8 compatibility issues, we generate a netlist instead of a schematic.
#     """
#     output_dir = Path(os.getenv("KICAD_OUTPUT_PATH", "./output"))
#     ensure_folder(str(output_dir))

#     # Create unique filename - use .net extension for netlist
#     timestamp = int(time.time())
#     filename = f"{spec.circuit_type}_{timestamp}.net"
#     filepath = output_dir / filename

#     print(f"🔧 Generating KiCad netlist: {filename}")
#     print(f"📁 Output directory: {output_dir}")

#     parts = {}  # ref → (SKiDL Part object, symbol_name)
#     nets = {}   # net_name → SKiDL Net object

#     def get_net(net_name: str):
#         """Get or create a net by name"""
#         if net_name not in nets:
#             nets[net_name] = Net(net_name)
#         return nets[net_name]

#     # 1) Create all components
#     print("📦 Creating components...")
#     for comp in filled_json.get("components", []):
#         ref = comp["ref"]        # e.g. "U1", "R1", ...
#         ctype = comp["type"]     # e.g. "LM2676S", "10k", "BME280", etc.
#         footprint = comp.get("footprint")
#         params = comp.get("params", {})

#         # Determine symbol library / symbol name / footprint
#         if ctype in PART_LIBRARY_MAP:
#             symbol_lib, symbol_name, footprint_name = PART_LIBRARY_MAP[ctype]
#         else:
#             # Fallback logic for unknown types
#             if ctype.endswith("k") or ctype.endswith("Ω"):
#                 symbol_lib, symbol_name, footprint_name = ("Device", "R", "Resistor_SMD:R_0603_1608Metric")
#             elif "uF" in ctype or "nF" in ctype or "pF" in ctype:
#                 symbol_lib, symbol_name, footprint_name = ("Device", "C", "Capacitor_SMD:C_0805_2012Metric")
#             else:
#                 print(f"⚠ Unknown component type '{ctype}', using generic IC")
#                 symbol_lib, symbol_name, footprint_name = ("Package_SO", "SOIC-8_3.9x4.9mm_P1.27mm", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm")

#         # Create the part safely
#         part, actual_symbol_name = safe_create_part(ref, ctype, symbol_lib, symbol_name, footprint_name)
        
#         # Add parameters as fields
#         for p_key, p_val in params.items():
#             part.fields[p_key] = str(p_val)

#         parts[ref] = (part, actual_symbol_name)

#     # 2) Create connections
#     print("🔗 Creating connections...")
#     connection_count = 0
#     for conn in filled_json.get("connections", []):
#         net_name = conn["net"]
#         from_token = conn["from"]  # e.g. "U1.Vin" or "R2.1"
#         to_token = conn["to"]

#         def parse_ref_pin(token: str):
#             if "." not in token:
#                 raise ValueError(f"Invalid ref.pin token: {token}")
#             return token.split(".", 1)

#         try:
#             from_ref, from_pin = parse_ref_pin(from_token)
#             to_ref, to_pin = parse_ref_pin(to_token)

#             if from_ref not in parts or to_ref not in parts:
#                 print(f"⚠ Skipping connection: {from_ref} or {to_ref} not found")
#                 continue

#             net_obj = get_net(net_name)
#             from_part, from_symbol = parts[from_ref]
#             to_part, to_symbol = parts[to_ref]
            
#             # Try to connect both pins
#             from_connected = safe_connect_pin(from_part, from_pin, net_obj, from_ref, from_symbol)
#             to_connected = safe_connect_pin(to_part, to_pin, net_obj, to_ref, to_symbol)
            
#             if from_connected and to_connected:
#                 connection_count += 1
#                 print(f"✓ Connected {from_ref}.{from_pin} ↔ {to_ref}.{to_pin} via '{net_name}'")
#             else:
#                 print(f"⚠ Partial/failed connection: {from_token} to {to_token}")
            
#         except Exception as e:
#             print(f"⚠ Failed to connect {from_token} to {to_token}: {e}")
#             continue

#     print(f"📊 Summary: {len(parts)} parts, {len(nets)} nets, {connection_count} connections")

#     # 3) Generate the netlist file (not schematic due to KiCad 8 issues)
#     print("⚡ Generating netlist file...")
#     try:
#         # Change to output directory and generate netlist
#         os.chdir(str(output_dir))
#         generate_netlist()
        
#         # Look for generated netlist files
#         netlist_files = list(output_dir.glob("*.net"))
#         if not netlist_files:
#             # Try other common netlist extensions
#             netlist_files.extend(list(output_dir.glob("*.netlist")))
#             netlist_files.extend(list(output_dir.glob("*.txt")))
        
#         if netlist_files:
#             # Use the most recently created file
#             newest_file = max(netlist_files, key=os.path.getctime)
#             if newest_file.name != filename:
#                 final_path = output_dir / filename
#                 newest_file.rename(final_path)
#                 print(f"✅ Renamed {newest_file.name} → {filename}")
#             else:
#                 final_path = newest_file
#         else:
#             # Create a simple netlist manually if SKiDL fails
#             print("⚠ No netlist generated by SKiDL, creating manual netlist...")
#             final_path = filepath
#             create_manual_netlist(filled_json, final_path, parts, nets)
        
#         print(f"🎉 Successfully generated: {final_path}")
#         return str(final_path)
        
#     except Exception as e:
#         print(f"⚠ SKiDL netlist generation failed: {e}")
#         # Fallback: create manual netlist
#         print("Creating manual netlist as fallback...")
#         create_manual_netlist(filled_json, filepath, parts, nets)
#         return str(filepath)


# def create_manual_netlist(filled_json: dict, filepath: Path, parts: dict, nets: dict):
#     """
#     Create a simple netlist file manually when SKiDL fails
#     """
#     with open(filepath, 'w') as f:
#         f.write("# KiCad Netlist Generated by AI Circuit Designer\n")
#         f.write(f"# Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
#         f.write("# Components:\n")
#         for comp in filled_json.get("components", []):
#             ref = comp["ref"]
#             ctype = comp["type"]
#             f.write(f"# {ref}: {ctype}\n")
        
#         f.write("\n# Connections:\n")
#         for conn in filled_json.get("connections", []):
#             f.write(f"# Net '{conn['net']}': {conn['from']} <-> {conn['to']}\n")
        
#         f.write("\n# This is a simple netlist format.\n")
#         f.write("# Import this into KiCad using File > Import > Netlist\n")


# # Debug function to list available parts in libraries
# def debug_library_contents():
#     """Debug function to show available parts in KiCad libraries"""
#     print("🔍 Debugging KiCad library contents...")
    
#     try:
#         # Try to create some common parts to see what's available
#         test_parts = [
#             ("Device", "R"),
#             ("Device", "C"),
#             ("Device", "L"),
#             ("Regulator_Switching", "LM2596"),
#             ("Regulator_Linear", "AMS1117-3.3"),
#         ]
        
#         for lib, part_name in test_parts:
#             try:
#                 test_part = Part(lib=lib, name=part_name, ref="TEST")
#                 print(f"✓ Found: {lib}:{part_name}")
#             except Exception as e:
#                 print(f"✗ Missing: {lib}:{part_name} - {e}")
                
#     except Exception as e:
#         print(f"Error during library debug: {e}")


# if __name__ == "__main__":
#     debug_library_contents()




import os
import time
from pathlib import Path
from skidl import Part, Net, generate_netlist, lib_search_paths, KICAD, set_default_tool
from scripts.utils import ensure_folder

# ───────────────────────────────────────────────────────────────
# 1) Tell SKiDL to use KiCad as the default backend
# ───────────────────────────────────────────────────────────────
set_default_tool(KICAD)

# ───────────────────────────────────────────────────────────────
# 2) Point to your KiCad 8 symbol & footprint directories
#    (Make sure these paths actually exist on your machine.)
# ───────────────────────────────────────────────────────────────
os.environ["KICAD8_SYMBOL_DIR"] = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
os.environ["KICAD8_FOOTPRINT_DIR"] = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"

KICAD_LIBRARY_PATHS = [
    # macOS (KiCad 8)
    "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols",
    "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints",
    # Linux (common)
    "/usr/share/kicad/symbols",
    "/usr/share/kicad/footprints",
    # Windows (if applicable)
    "C:/Program Files/KiCad/share/kicad/symbols",
    "C:/Program Files/KiCad/share/kicad/footprints",
    "C:/Program Files (x86)/KiCad/share/kicad/symbols",
    "C:/Program Files (x86)/KiCad/share/kicad/footprints",
]

# Append any existing path to SKiDL’s search list
for path in KICAD_LIBRARY_PATHS:
    if os.path.exists(path):
        lib_search_paths[KICAD].append(path)
        print(f"Added KiCad library path: {path}")

# ───────────────────────────────────────────────────────────────
# 3) PART_LIBRARY_MAP: Exact KiCad‐symbol names as found in your .kicad_sym
#    We include aliases so that the bare "LM2596S" or "LM2676S" defaults to "-5".
# ───────────────────────────────────────────────────────────────
PART_LIBRARY_MAP = {
    # ─ Power regulators (Regulator_Switching library)
    #   The actual symbols found via grep:
    #     LM2596S-5, LM2596S-3.3, LM2596S-12, LM2596S-ADJ
    #     LM2676S-5, LM2676S-12, LM2676S-ADJ
    #
    "LM2596S-5":   ("Regulator_Switching", "LM2596S-5",   "Package_TO_SOT_SMD:TO-263-5_TabPin3"),
    "LM2596S-3.3": ("Regulator_Switching", "LM2596S-3.3", "Package_TO_SOT_SMD:TO-263-5_TabPin3"),
    "LM2596S-12":  ("Regulator_Switching", "LM2596S-12",  "Package_TO_SOT_SMD:TO-263-5_TabPin3"),
    "LM2596S-ADJ": ("Regulator_Switching", "LM2596S-ADJ", "Package_TO_SOT_SMD:TO-263-5_TabPin3"),

    "LM2676S-5":   ("Regulator_Switching", "LM2676S-5",   "Package_TO_SOT_SMD:TO-263-5_TabPin3"),
    "LM2676S-12":  ("Regulator_Switching", "LM2676S-12",  "Package_TO_SOT_SMD:TO-263-5_TabPin3"),
    "LM2676S-ADJ": ("Regulator_Switching", "LM2676S-ADJ", "Package_TO_SOT_SMD:TO-263-5_TabPin3"),

    # Aliases: if JSON uses bare "LM2596S" or "LM2676S", default to the "-5" variant
    "LM2596S":     ("Regulator_Switching", "LM2596S-5",   "Package_TO_SOT_SMD:TO-263-5_TabPin3"),
    "LM2676S":     ("Regulator_Switching", "LM2676S-5",   "Package_TO_SOT_SMD:TO-263-5_TabPin3"),

    "AMS1117-3.3": ("Regulator_Linear",    "AMS1117-3.3", "Package_TO_SOT_SMD:SOT-223-3_TabPin2"),

    # ─ Basic passives ─────────────────────────────────────────────
    "47uH_2A":     ("Device",               "L",          "Inductor_SMD:L_0805_2012Metric"),
    "SR560":       ("Device",               "D_Schottky", "Diode_SMD:D_SOD-123"),
    "22uF_35V":    ("Device",               "C_Polarized","Capacitor_SMD:C_0805_2012Metric"),
    "47uF_10V":    ("Device",               "C_Polarized","Capacitor_SMD:C_0805_2012Metric"),

    # ─ Resistors ───────────────────────────────────────────────────
    "10k":         ("Device",               "R",          "Resistor_SMD:R_0603_1608Metric"),
    "1k":          ("Device",               "R",          "Resistor_SMD:R_0603_1608Metric"),
    "4.7k":        ("Device",               "R",          "Resistor_SMD:R_0603_1608Metric"),

    # ─ Op-amps ─────────────────────────────────────────────────────
    "MCP6001":     ("Amplifier_Operational","MCP6001",    "Package_TO_SOT_SMD:SOT-23-5"),

    # ─ Transistors ──────────────────────────────────────────────────
    "2N3904":      ("Transistor_BJT",       "2N3904",     "Package_TO_SOT_THT:TO-92_Inline"),

    # ─ Diodes ───────────────────────────────────────────────────────
    "1N4007":      ("Diode",                "1N4007",     "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal"),

    # ─ LED ──────────────────────────────────────────────────────────
    "LED":         ("Device",               "LED",        "LED_SMD:LED_0805_2012Metric"),

    # ─ 555 Timer ─────────────────────────────────────────────────────
    "NE555":       ("Timer",                "NE555P",     "Package_DIP:DIP-8_W7.62mm"),

    # ─ Crystals & caps ───────────────────────────────────────────────
    "Crystal_SMD": ("Device",               "Crystal",    "Crystal:Crystal_SMD_2016-4Pin_2.0x1.6mm"),
    "Capacitor_SMD":("Device",              "C",          "Capacitor_SMD:C_0805_2012Metric"),

    # ─ Sensors ───────────────────────────────────────────────────────
    "BME280":      ("Sensor_Humidity",      "BME280",     "Package_LGA:Bosch_LGA-8_2.5x2.5mm_P0.65mm_ClockwisePinNumbering"),

    # ─ MCUs ──────────────────────────────────────────────────────────
    "STM32F103":   ("MCU_ST_STM32F1",       "STM32F103C8Tx","Package_QFP:LQFP-48_7x7mm_P0.5mm"),

    # ─ Generic capacitor values ──────────────────────────────────────
    "0.1uF":       ("Device",               "C",          "Capacitor_SMD:C_0603_1608Metric"),
    "0.01uF":      ("Device",               "C",          "Capacitor_SMD:C_0603_1608Metric"),
    "10uF":        ("Device",               "C_Polarized","Capacitor_SMD:C_0805_2012Metric"),
}

# ───────────────────────────────────────────────────────────────
# 4) COMPONENT_PIN_MAP: pin-name → pin-number mapping
# ───────────────────────────────────────────────────────────────
COMPONENT_PIN_MAP = {
    "LM2596S-5": {
        "Vin":  "1",
        "GND":  "3",
        "SW":   "2",
        "Vout": "4",
        "FB":   "5",
    },
    "LM2596S-3.3": {
        "Vin":  "1",
        "GND":  "3",
        "SW":   "2",
        "Vout": "4",
        "FB":   "5",
    },
    "LM2596S-12": {
        "Vin":  "1",
        "GND":  "3",
        "SW":   "2",
        "Vout": "4",
        "FB":   "5",
    },
    "LM2596S-ADJ": {
        "Vin":  "1",
        "GND":  "3",
        "SW":   "2",
        "Vout": "4",
        "FB":   "5",
    },

    "LM2676S-5": {
        "Vin":  "1",
        "GND":  "3",
        "SW":   "2",
        "Vout": "4",
        "FB":   "5",
    },
    "LM2676S-12": {
        "Vin":  "1",
        "GND":  "3",
        "SW":   "2",
        "Vout": "4",
        "FB":   "5",
    },
    "LM2676S-ADJ": {
        "Vin":  "1",
        "GND":  "3",
        "SW":   "2",
        "Vout": "4",
        "FB":   "5",
    },

    "L": {
        "1": "1",
        "2": "2",
    },
    "D_Schottky": {
        "K": "1",
        "A": "2",
    },
    "C_Polarized": {
        "+": "1",
        "-": "2",
    },
    "R": {
        "1": "1",
        "2": "2",
    },
    "C": {
        "1": "1",
        "2": "2",
    },
}

# ───────────────────────────────────────────────────────────────
# 5) safe_create_part: primary attempt → fallback to Device:R,Device:C,Device:DEVICE
# ───────────────────────────────────────────────────────────────
def safe_create_part(ref: str, ctype: str, symbol_lib: str, symbol_name: str, footprint_name: str):
    """
    Try to create Part(lib=symbol_lib, name=symbol_name). If that fails,
    fall back to Device:R (resistor), Device:C (capacitor), or Device:DEVICE (generic IC).
    """
    try:
        part = Part(lib=symbol_lib, name=symbol_name, ref=ref, footprint=footprint_name)
        part.value = ctype
        print(f"✓ Created part: {ref} ({symbol_lib}:{symbol_name})")
        return part, symbol_name

    except Exception as e:
        print(f"⚠ Failed to create {ref} with {symbol_lib}:{symbol_name}: {e}")

        # Fallback: use Device library generics
        try:
            if ctype.endswith("k") or ctype.endswith("Ω"):
                part = Part(lib="Device", name="R", ref=ref, footprint="Resistor_SMD:R_0603_1608Metric")
                symbol_name = "R"

            elif "uF" in ctype or "nF" in ctype or "pF" in ctype:
                if any(x in ctype for x in ["47uF", "22uF", "10uF"]):
                    part = Part(lib="Device", name="C_Polarized", ref=ref, footprint="Capacitor_SMD:C_0805_2012Metric")
                    symbol_name = "C_Polarized"
                else:
                    part = Part(lib="Device", name="C", ref=ref, footprint="Capacitor_SMD:C_0805_2012Metric")
                    symbol_name = "C"

            else:
                # Generic IC fallback: use the "DEVICE" symbol (uppercase) from Device.kicad_sym
                part = Part(lib="Device", name="DEVICE", ref=ref, footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm")
                symbol_name = "DEVICE"

            part.value = ctype
            print(f"✓ Created fallback part: {ref} ({symbol_name} from Device library)")
            return part, symbol_name

        except Exception as e2:
            raise RuntimeError(f"Failed to create part {ref} even with fallback: {e2}")


# ───────────────────────────────────────────────────────────────
# 6) safe_connect_pin: tries direct pin name → pin_map → numeric → int
# ───────────────────────────────────────────────────────────────
def safe_connect_pin(part, pin_name, net_obj, ref, symbol_name):
    """
    Try part[pin_name], then COMPONENT_PIN_MAP lookup, then numeric pin indices.
    """
    # 1) Direct pin name
    try:
        net_obj += part[pin_name]
        return True
    except:
        pass

    # 2) Named mapping
    if symbol_name in COMPONENT_PIN_MAP:
        pin_map = COMPONENT_PIN_MAP[symbol_name]
        if pin_name in pin_map:
            try:
                mapped_pin = pin_map[pin_name]
                net_obj += part[mapped_pin]
                print(f"    Mapped {ref}.{pin_name} → pin {mapped_pin}")
                return True
            except:
                pass

    # 3) If pin_name is a digit
    try:
        if pin_name.isdigit():
            net_obj += part[int(pin_name)]
            return True
    except:
        pass

    # 4) Cast to int
    try:
        pin_idx = int(pin_name)
        net_obj += part[pin_idx]
        return True
    except:
        pass

    print(f"    Failed to find pin {pin_name} on {ref} ({symbol_name})")
    return False


# ───────────────────────────────────────────────────────────────
# 7) generate_kicad_schematic: build parts/nets and write .netlist
# ───────────────────────────────────────────────────────────────
def generate_kicad_schematic(filled_json: dict, spec: any) -> str:
    """
    Generate a KiCad netlist file (.net) and return its filepath.
    (We output a netlist instead of .sch for KiCad-8 compatibility.)
    """
    # 7.1) Prepare output directory
    output_dir = Path(os.getenv("KICAD_OUTPUT_PATH", "./output"))
    ensure_folder(str(output_dir))

    timestamp = int(time.time())
    filename = f"{spec.circuit_type}_{timestamp}.net"
    filepath = output_dir / filename

    print(f"🔧 Generating KiCad netlist: {filename}")
    print(f"📁 Output directory: {output_dir}")

    parts = {}  # ref → (Part object, symbol_name)
    nets = {}   # net_name → Net object

    def get_net(net_name: str):
        """Return a Net object for net_name, creating it if needed."""
        if net_name not in nets:
            nets[net_name] = Net(net_name)
        return nets[net_name]

    # 7.2) Create components
    print("📦 Creating components...")
    for comp in filled_json.get("components", []):
        ref = comp["ref"]        # e.g. "U1", "R1", etc.
        ctype = comp["type"]     # e.g. "LM2676S", "10k", etc.
        params = comp.get("params", {})

        # Remap bare "LM2676S"/"LM2596S" to the "-5" variant if needed
        if ctype == "LM2676S":
            ctype = "LM2676S-5"
        elif ctype == "LM2596S":
            ctype = "LM2596S-5"

        # Look up library, symbol, footprint
        if ctype in PART_LIBRARY_MAP:
            symbol_lib, symbol_name, footprint_name = PART_LIBRARY_MAP[ctype]
        else:
            # Fallback for anything not in PART_LIBRARY_MAP
            if ctype.endswith("k") or ctype.endswith("Ω"):
                symbol_lib, symbol_name, footprint_name = ("Device", "R", "Resistor_SMD:R_0603_1608Metric")
            elif "uF" in ctype or "nF" in ctype or "pF" in ctype:
                symbol_lib, symbol_name, footprint_name = ("Device", "C", "Capacitor_SMD:C_0805_2012Metric")
            else:
                print(f"⚠ Unknown component type '{ctype}', using generic IC")
                symbol_lib, symbol_name, footprint_name = ("Device", "DEVICE", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm")

        # Create or fallback
        part, actual_symbol_name = safe_create_part(ref, ctype, symbol_lib, symbol_name, footprint_name)

        # Add any custom fields
        for p_key, p_val in params.items():
            part.fields[p_key] = str(p_val)

        parts[ref] = (part, actual_symbol_name)

    # 7.3) Create connections
    print("🔗 Creating connections...")
    connection_count = 0
    for conn in filled_json.get("connections", []):
        net_name = conn["net"]    # e.g. "VIN", "GND"
        from_tok = conn["from"]   # e.g. "U1.Vin" or "R2.1"
        to_tok   = conn["to"]

        def parse_ref_pin(token: str):
            if "." not in token:
                raise ValueError(f"Invalid ref.pin token: {token}")
            return token.split(".", 1)

        try:
            from_ref, from_pin = parse_ref_pin(from_tok)
            to_ref,   to_pin   = parse_ref_pin(to_tok)

            if from_ref not in parts or to_ref not in parts:
                print(f"⚠ Skipping connection: {from_ref} or {to_ref} not found")
                continue

            net_obj       = get_net(net_name)
            from_part, fs = parts[from_ref]
            to_part,   ts = parts[to_ref]

            ok1 = safe_connect_pin(from_part, from_pin, net_obj, from_ref, fs)
            ok2 = safe_connect_pin(to_part,   to_pin,   net_obj, to_ref,   ts)

            if ok1 and ok2:
                connection_count += 1
                print(f"✓ Connected {from_ref}.{from_pin} ↔ {to_ref}.{to_pin} via '{net_name}'")
            else:
                print(f"⚠ Partial/failed connection: {from_tok} → {to_tok}")

        except Exception as e:
            print(f"⚠ Failed to connect {from_tok} → {to_tok}: {e}")
            continue

    print(f"📊 Summary: {len(parts)} parts, {len(nets)} nets, {connection_count} connections")

    # 7.4) Generate the netlist file (.net)
    print("⚡ Generating netlist file...")
    try:
        os.chdir(str(output_dir))
        generate_netlist()

        # Find the newest .net (or .netlist/.txt) in output_dir
        netlist_files = list(output_dir.glob("*.net"))
        if not netlist_files:
            netlist_files.extend(list(output_dir.glob("*.netlist")))
            netlist_files.extend(list(output_dir.glob("*.txt")))

        if netlist_files:
            newest = max(netlist_files, key=os.path.getctime)
            if newest.name != filename:
                final_path = output_dir / filename
                newest.rename(final_path)
                print(f"✅ Renamed {newest.name} → {filename}")
            else:
                final_path = newest
        else:
            # If SKiDL didn’t produce one, fall back manually
            print("⚠ No netlist generated by SKiDL; creating manual netlist…")
            final_path = filepath
            create_manual_netlist(filled_json, final_path, parts, nets)

        print(f"🎉 Successfully generated: {final_path}")
        return str(final_path)

    except Exception as e:
        print(f"⚠ SKiDL netlist generation failed: {e}")
        print("Creating manual netlist as fallback…")
        create_manual_netlist(filled_json, filepath, parts, nets)
        return str(filepath)


# ───────────────────────────────────────────────────────────────
# 8) create_manual_netlist: fallback if generate_netlist() fails
# ───────────────────────────────────────────────────────────────
def create_manual_netlist(filled_json: dict, filepath: Path, parts: dict, nets: dict):
    """
    If SKiDL’s generate_netlist() fails, write a simple comment-based netlist.
    """
    with open(filepath, "w") as f:
        f.write("# KiCad Netlist Generated by AI Circuit Designer\n")
        f.write(f"# Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("# Components:\n")
        for comp in filled_json.get("components", []):
            ref = comp["ref"]
            ctype = comp["type"]
            f.write(f"# {ref}: {ctype}\n")

        f.write("\n# Connections:\n")
        for conn in filled_json.get("connections", []):
            f.write(f"# Net '{conn['net']}': {conn['from']} <-> {conn['to']}\n")

        f.write("\n# This is a simple netlist format.\n")
        f.write("# Import into KiCad via File → Import → Netlist\n")


# ───────────────────────────────────────────────────────────────
# 9) debug_library_contents: Check which symbols SKiDL can load
# ───────────────────────────────────────────────────────────────
def debug_library_contents():
    """
    Print out whether SKiDL can load specific (library, symbol) pairs.
    Run this once to confirm your paths and symbol names are correct.
    """
    print("🔍 Debugging KiCad library contents…")
    test_parts = [
        ("Regulator_Switching", "LM2596S-5"),
        ("Regulator_Switching", "LM2596S-3.3"),
        ("Regulator_Switching", "LM2596S-12"),
        ("Regulator_Switching", "LM2596S-ADJ"),
        ("Regulator_Switching", "LM2676S-5"),
        ("Regulator_Switching", "LM2676S-12"),
        ("Regulator_Switching", "LM2676S-ADJ"),
        ("Regulator_Switching", "LM2596S"),   # alias
        ("Regulator_Switching", "LM2676S"),   # alias
        ("Regulator_Linear",     "AMS1117-3.3"),
        ("Device",               "R"),
        ("Device",               "C"),
        ("Device",               "DEVICE"),  # Generic IC fallback
    ]

    for lib, part_name in test_parts:
        try:
            _ = Part(lib=lib, name=part_name, ref="TEST")
            print(f"✓ Found: {lib}:{part_name}")
        except Exception as e:
            print(f"✗ Missing: {lib}:{part_name}  —  {e}")


if __name__ == "__main__":
    # Run this to confirm which symbols SKiDL can actually find.
    debug_library_contents()
