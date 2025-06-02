#!/usr/bin/env python3
"""
json_to_pcb.py

Given a JSON description of a buck converter (or any circuit),
this script will produce a minimal KiCad PCB (`.kicad_pcb`) that:

  • Places each footprint on a simple grid
  • Creates nets and assigns each pad to its corresponding net
  • Leaves “ratsnest” connections visible (no actual copper tracks are drawn)

You can then open the generated `output.kicad_pcb` in KiCad’s PCB editor
and route the connections as you wish.

Requirements:
  • This script must be run with a Python interpreter that knows about `pcbnew`.
    For example, on Linux/macOS you might do:
      
      $ export PYTHONPATH="/usr/lib/kicad-nightly/lib/python3/dist-packages"
      $ python3 json_to_pcb.py

    Adjust the `PYTHONPATH` to point to your KiCad installation’s `python` folder,
    or simply use the “Python Console” inside KiCad, etc., so that `import pcbnew` works.

Usage:
  1. Make the JSON below match your actual JSON structure (or load it from a file).
  2. Run this script.
  3. Open `output.kicad_pcb` in KiCad’s PCB editor.
"""

import json
import pcbnew
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# 1) Paste or load your JSON here. This example uses exactly the JSON you gave.
#    You could also do: 
#       with open("input.json") as f: data = json.load(f)
# ──────────────────────────────────────────────────────────────────────────────
data = {
    "filledTemplate": {
        "circuit_type": "buck_converter",
        "components": [
            {
                "footprint": "Regulator_Boards:LM2676S_PowerPad",
                "params": { "Iout": "2A", "Vin": "12V", "Vout": "5V" },
                "ref": "U1",
                "type": "LM2676S"
            },
            {
                "connections": ["SW", "Vout"],
                "footprint": "Inductor_SMD:L_0805",
                "ref": "L1",
                "type": "47uH_2A"
            },
            {
                "connections": ["SW", "GND"],
                "footprint": "Diode_SMD:BAT54",
                "ref": "D1",
                "type": "SR560"
            },
            {
                "connections": ["Vin", "GND"],
                "footprint": "Capacitor_SMD:C_0805",
                "ref": "C1",
                "type": "22uF_35V"
            },
            {
                "connections": ["Vout", "GND"],
                "footprint": "Capacitor_SMD:C_0805",
                "ref": "C2",
                "type": "47uF_10V"
            }
        ],
        "connections": [
            { "from": "U1.Vin",  "net": "Vin",  "to": "C1.+" },
            { "from": "U1.GND",  "net": "GND",  "to": "C1.-" },
            { "from": "U1.SW",   "net": "SW",   "to": "L1.1" },
            { "from": "L1.2",    "net": "Vout", "to": "C2.+" },
            { "from": "L1.2",    "net": "GND",  "to": "C2.-" },
            { "from": "U1.Vout", "net": "Vout", "to": "C2.+" }
        ],
        "description": "Step-down (buck) DC–DC converter",
        "placeholders": {
          "input_voltage": None,
          "output_current": None,
          "output_voltage": None
        }
    },
    "kicad_sch_url": "/download/buck_converter_1748703256.kicad_sch",
    "spec": {
        "Vin": None,
        "Vout": None,
        "circuit_type": "buck_converter",
        "clock_freq": None,
        "cutoff_frequency": None,
        "filter_capacitance": None,
        "frequency": None,
        "gain": None,
        "input_ac": None,
        "input_signal": None,
        "input_voltage": "12V",
        "led_current": None,
        "mcu": None,
        "output_current": "2A",
        "output_voltage": "5V",
        "reference_voltage": None,
        "resistor_value": None,
        "sensor": None,
        "threshold_high": None,
        "threshold_low": None
    }
}

# Convenience variables
filled = data["filledTemplate"]
components = filled["components"]
connections = filled["connections"]


# ──────────────────────────────────────────────────────────────────────────────
# 2) Create a brand‐new PCB board
# ──────────────────────────────────────────────────────────────────────────────
board = pcbnew.BOARD()


# Optionally set some metadata
board.SetDesignSettings(
    pcbnew.DESIGN_SETTINGS(
        default_net_class="Default",     # You can change net classes if desired
        interactive_router=True
    )
)
board.SetTitle(filled["description"])  # Set the board title to the description


# ──────────────────────────────────────────────────────────────────────────────
# 3) Parse components: load footprints, assign references, and place them on a grid
# ──────────────────────────────────────────────────────────────────────────────
#
# We will place each part on a simple 10 mm × 10 mm grid for clarity.
# Feel free to adjust the grid spacing or positions to suit your layout.

GRID_X_SPACING = 20  # mm
GRID_Y_SPACING = 20  # mm

def mm_to_coord(x_mm, y_mm):
    """Convert millimeters to pcbnew internal coordinates (nanometers)."""
    return pcbnew.wxPoint(int(pcbnew.FromMM(x_mm)), int(pcbnew.FromMM(y_mm)))


# Keep a dictionary from reference → footprint module so we can assign nets later
ref_to_module = {}

# Loop through each component in JSON and place it
x_idx = 0
y_idx = 0

for comp in components:
    ref     = comp["ref"]         # e.g. "U1", "L1", "D1", etc.
    footprint_full = comp["footprint"]  # e.g. "Regulator_Boards:LM2676S_PowerPad"
    
    # Some JSONs might omit the "library:" prefix—KiCad can still find it if installed in default path.
    # We’ll pass exactly footprint_full to FootprintLoad. 
    # (KiCad’s default search paths will resolve e.g. "Diode_SMD:BAT54" etc.)
    #
    footprint_lib, footprint_name = footprint_full.split(":")
    
    # Use pcbnew.FootprintLoad("", "Library:Name") to let KiCad search its default libs
    module = pcbnew.FootprintLoad("", footprint_full)
    if module is None:
        raise ValueError(f"Could not load footprint '{footprint_full}' for {ref}")

    # Assign the reference designator
    module.SetReference(ref)

    # Place it on the board at (x_idx, y_idx) grid
    pos = mm_to_coord(x_idx * GRID_X_SPACING, y_idx * GRID_Y_SPACING)
    module.SetPosition(pos)

    board.Add(module)
    ref_to_module[ref] = module

    # Advance the grid: move in X; wrap around every 5 parts
    x_idx += 1
    if x_idx >= 5:
        x_idx = 0
        y_idx += 1


# ──────────────────────────────────────────────────────────────────────────────
# 4) Create nets and assign pads according to the JSON “connections”
# ──────────────────────────────────────────────────────────────────────────────
#
# We will:
#   • Iterate through each connection record (e.g. { "from": "U1.Vin", "net": "Vin", "to": "C1.+" })
#   • For each distinct net name (“Vin”, “GND”, “SW”, “Vout”), we either find or create a NETINFO_ITEM.
#   • Grab the pad on the “from” module and on the “to” module, and set both pads to that net.
#
#   Note: Pad‐naming must match exactly the pad names inside the footprint. If the footprint uses numeric
#   pad numbers (like “1”, “2”), then JSON must use those. In your JSON you have “U1.Vin” or “C1.+”,
#   so this assumes that in the Regulator_Boards:LM2676S_PowerPad footprint, one pad is actually named “Vin”,
#   another “GND”, “SW”, etc., and that for the capacitors, KiCad uses “+” and “–” pad names (common for polarized).
#

# Keep a dictionary of net_name → NETINFO_ITEM on this board
net_dict = {}

def get_or_create_net(board, net_name):
    """
    Return a NETINFO_ITEM for net_name, creating it if it doesn’t exist yet.
    """
    if net_name in net_dict:
        return net_dict[net_name]

    # Create a new net on the board
    net = pcbnew.NETINFO_ITEM(board, net_name)
    board.Add(net)
    net_dict[net_name] = net
    return net

# Assign pads to nets
for conn in connections:
    net_name = conn["net"]
    from_token = conn["from"]  # e.g. "U1.Vin"
    to_token   = conn["to"]    # e.g. "C1.+"

    # Helper to parse "Ref.PadName" → (ref, pad_name)
    def parse_ref_pin(token: str):
        if "." not in token:
            raise ValueError(f"Invalid token format (no dot): {token}")
        return tuple(token.split(".", 1))

    from_ref, from_pin = parse_ref_pin(from_token)
    to_ref,   to_pin   = parse_ref_pin(to_token)

    # Find the modules by reference
    if from_ref not in ref_to_module or to_ref not in ref_to_module:
        raise ValueError(f"Component reference not found: {from_ref} or {to_ref}")

    mod_from = ref_to_module[from_ref]
    mod_to   = ref_to_module[to_ref]

    # Make sure the net exists on the board
    net = get_or_create_net(board, net_name)

    # Helper: find a pad on a module by pad‐name or by pad‐number
    def find_pad(module, pad_name):
        """
        Try module.FindPadByName(pad_name). If that fails, try module.FindPadByNumber(pad_name).
        """
        pad = module.FindPadByName(pad_name)
        if pad is None:
            pad = module.FindPadByNumber(pad_name)
        if pad is None:
            raise ValueError(f"Pad '{pad_name}' not found on module '{module.GetReference()}'")
        return pad

    pad_from = find_pad(mod_from, from_pin)
    pad_to   = find_pad(mod_to,   to_pin)

    # Assign those pads to the net
    pad_from.SetNet(net)
    pad_to.SetNet(net)

# ──────────────────────────────────────────────────────────────────────────────
# 5) Save out the board to “output.kicad_pcb”
# ──────────────────────────────────────────────────────────────────────────────
output_path = Path("output.kicad_pcb")
pcbnew.SaveBoard(str(output_path), board)
print(f"✅ Board written to {output_path.resolve()}")
