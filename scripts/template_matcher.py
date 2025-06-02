# scripts/template_matcher.py

import os
import json
from typing import Dict, Any
from scripts.utils import load_json, replace_placeholders


def compute_divider_R2_value(Vin: str, Vout: str) -> str:
    """
    Computes R2 (in kΩ) for a 10k R1 voltage divider:
    R2 = R1 * (Vout / (Vin - Vout))
    Returns a string like "7.14".
    """
    try:
        vin_val = float(Vin.strip().upper().replace("V", ""))
        vout_val = float(Vout.strip().upper().replace("V", ""))
    except ValueError:
        raise ValueError(f"Invalid Vin/Vout: '{Vin}', '{Vout}'")

    if vout_val >= vin_val:
        raise ValueError("Vout must be less than Vin for a voltage divider.")

    r1_k = 10.0  # R1 = 10kΩ (fixed)
    r2_k = (r1_k * vout_val) / (vin_val - vout_val)
    return f"{round(r2_k, 2)}"  # e.g. "7.14"


def compute_low_pass_values(cutoff_khz: str) -> Dict[str, str]:
    """
    For a first-order RC low-pass filter at cutoff_frequency (in kHz),
    pick C1 = 10 nF and compute R1 = 1/(2π f C)
    Returns {"R1_value": "<kΩ>", "C1_value": "10"}
    """
    try:
        f_khz = float(cutoff_khz)
    except ValueError:
        raise ValueError(f"Invalid cutoff_frequency: '{cutoff_khz}'")
    # Convert kHz to Hz
    f_hz = f_khz * 1e3
    C1_f = 10e-9  # 10 nF
    R1 = 1.0 / (2 * 3.141592653589793 * f_hz * C1_f)  # in ohms
    R1_k = R1 / 1e3
    return {"R1_value": f"{round(R1_k, 2)}", "C1_value": "10"}


def compute_high_pass_values(cutoff_khz: str) -> Dict[str, str]:
    """
    For a first-order RC high-pass filter at cutoff_frequency (in kHz),
    pick R1 = 10 kΩ and compute C1 = 1/(2π f R)
    Returns {"R1_value": "10", "C1_value": "<nF>"}
    """
    try:
        f_khz = float(cutoff_khz)
    except ValueError:
        raise ValueError(f"Invalid cutoff_frequency: '{cutoff_khz}'")
    f_hz = f_khz * 1e3
    R1 = 10e3  # 10 kΩ
    C1 = 1.0 / (2 * 3.141592653589793 * f_hz * R1)  # in Farads
    C1_n = C1 * 1e9
    return {"R1_value": "10", "C1_value": f"{round(C1_n, 2)}"}


def compute_555_astable_values(freq_hz: str) -> Dict[str, str]:
    """
    For a 555 astable configuration with frequency f (in Hz),
    choose C1 = 0.01 µF, and for 50% duty cycle, set R1 = R2:
      f = 1.44 / ( (R1 + 2R2) * C1 )
    If R1=R2, then R => solve R = 1.44 / (3 * f * C1)
    Returns {"R1_value": "<kΩ>", "R2_value": "<kΩ>", "C1_value": "0.01"}
    """
    try:
        f = float(freq_hz)
    except ValueError:
        raise ValueError(f"Invalid frequency: '{freq_hz}'")
    C1 = 0.01e-6  # 0.01 µF
    R = 1.44 / (3 * f * C1)  # in ohms
    R_k = R / 1e3
    return {"R1_value": f"{round(R_k, 2)}", "R2_value": f"{round(R_k, 2)}", "C1_value": "0.01"}


def compute_led_blinker_values(freq_hz: str, led_current_ma: str) -> Dict[str, str]:
    """
    For a 555 astable LED blinker at frequency f (Hz) and LED current (mA):
    Pick C1 = 0.01 µF (like above), solve R1 = R2 = 1.44 / (3fC1) for 50% duty.
    Then choose R3 = (VCC - Vforward) / Iled. Assume VCC=5V, Vforward=2V.
    Returns {"R1_value": "<kΩ>", "R2_value": "<kΩ>", "C1_value": "0.01", "R3_value": "<kΩ>"}
    """
    try:
        f = float(freq_hz)
        i_led = float(led_current_ma) / 1000.0  # convert to A
    except ValueError:
        raise ValueError(f"Invalid frequency or led_current: '{freq_hz}', '{led_current_ma}'")
    # 555 astable portion
    C1 = 0.01e-6
    R = 1.44 / (3 * f * C1)  # in ohms
    R_k = R / 1e3

    # LED resistor (assuming VCC=5V, Vf=2V)
    Vcc = 5.0
    Vf = 2.0
    if i_led <= 0:
        raise ValueError("led_current must be > 0")
    R3 = (Vcc - Vf) / i_led  # ohms
    R3_k = R3 / 1e3

    return {
        "R1_value": f"{round(R_k, 2)}",
        "R2_value": f"{round(R_k, 2)}",
        "C1_value": "0.01",
        "R3_value": f"{round(R3_k, 2)}"
    }


def compute_comparator_values(th_high: str, th_low: str, supply: str) -> Dict[str, str]:
    """
    For a simple comparator using R1 and R2 as a voltage divider on V+,
    such that Vth = R2 / (R1+R2) * Vout. 
    If we want hysteresis, pick R1=R2 for equal thresholds (simple case).
    Returns {"R1_value": "10", "R2_value": "10"} as placeholders.
    (A more accurate design would solve R1/R2 for the exact thresholds.)
    """
    # This is a stub. To implement accurately, solve:
    # Vth_high = R2/(R1+R2)*Vout... etc. For now, use 10k for both.
    return {"R1_value": "10", "R2_value": "10"}


def match_and_fill_template(spec: Any) -> Dict[str, Any]:
    """
    1) Load JSON template from ./templates/<circuit_type>.json
    2) Build values dict from spec fields
    3) Compute any derived placeholder values (e.g. R2_value, filter caps, etc.)
    4) Recursively replace placeholders
    5) Return the filled JSON
    """
    template_dir = os.getenv("KICAD_TEMPLATE_PATH", "./templates")
    template_path = os.path.join(template_dir, f"{spec.circuit_type}.json")
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found for '{spec.circuit_type}'")

    template = load_json(template_path)

    # Build placeholder→value mapping
    values: Dict[str, str] = {}
    # Basic mappings
    for key in [
        "input_voltage", "output_voltage", "output_current",
        "gain", "mcu", "sensor", "clock_freq",
        "Vin", "Vout", "input_ac", "reference_voltage",
        "threshold_high", "threshold_low", "input_signal",
        "resistor_value", "led_current", "filter_capacitance"
    ]:
        val = getattr(spec, key, None)
        if val is not None:
            values[key] = val

    # Special computations:
    ct = spec.circuit_type

    # Voltage divider
    if ct == "voltage_divider":
        Vin = spec.Vin
        Vout = spec.Vout
        if not Vin or not Vout:
            raise ValueError("Vin and Vout are required for voltage_divider.")
        values["R2_value"] = compute_divider_R2_value(Vin, Vout)

    # Low-pass filter
    if ct == "low_pass_filter":
        cf = spec.cutoff_frequency
        if not cf:
            raise ValueError("cutoff_frequency required for low_pass_filter.")
        lp = compute_low_pass_values(cf)
        values.update(lp)

    # High-pass filter
    if ct == "high_pass_filter":
        cf = spec.cutoff_frequency
        if not cf:
            raise ValueError("cutoff_frequency required for high_pass_filter.")
        hp = compute_high_pass_values(cf)
        values.update(hp)

    # 555 timer astable
    if ct == "555_timer_astable":
        freq = spec.frequency
        if not freq:
            raise ValueError("frequency required for 555_timer_astable.")
        tvals = compute_555_astable_values(freq)
        values.update(tvals)

    # LED blinker (555)
    if ct == "led_blinker_555":
        freq = spec.frequency
        ic = spec.led_current
        if not freq or not ic:
            raise ValueError("frequency and led_current required for led_blinker_555.")
        lv = compute_led_blinker_values(freq, ic)
        values.update(lv)

    # Comparator
    if ct == "comparator":
        th_high = spec.threshold_high
        th_low = spec.threshold_low
        supply = spec.supply_voltage if hasattr(spec, "supply_voltage") else None
        if not th_high or not th_low or not supply:
            raise ValueError("threshold_high, threshold_low, and supply_voltage required for comparator.")
        comp_vals = compute_comparator_values(th_high, th_low, supply)
        values.update(comp_vals)

    # Comparator (noninverting)
    if ct == "comparator_noninverting":
        ref_v = spec.reference_voltage
        in_sig = spec.input_signal
        supply = spec.supply_voltage
        if not ref_v or not in_sig or not supply:
            raise ValueError("reference_voltage, input_signal, and supply_voltage required for comparator_noninverting.")
        comp_vals = compute_comparator_values(ref_v, None, supply)
        values.update(comp_vals)

    # Astable multivibrator (two-transistor)
    if ct == "astable_multivibrator":
        rv = spec.resistor_value
        if not rv:
            raise ValueError("resistor_value required for astable_multivibrator.")
        # For simplicity, just pass resistor_value through (user chooses it)
        # You could compute an approximate frequency if needed.
        values["resistor_value"] = rv

    # Bridge rectifier & voltage_multiplier & microcontroller_board only substitute placeholders
    # No numeric computations needed.

    # Finally, replace placeholders in the entire template
    filled = replace_placeholders(template, values)
    return filled
