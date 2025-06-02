import os
import json
import requests
from pydantic import BaseModel, field_validator, model_validator
from dotenv import load_dotenv
from typing import Optional


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# Define the expected structure of the parsed circuit specification
class CircuitSpec(BaseModel):
    circuit_type: str
    input_voltage: Optional[str] = None
    output_voltage: Optional[str] = None
    output_current: Optional[str] = None
    gain: Optional[str] = None
    mcu: Optional[str] = None
    sensor: Optional[str] = None
    clock_freq: Optional[str] = None
    Vin: Optional[str] = None
    Vout: Optional[str] = None
    cutoff_frequency: Optional[str] = None
    frequency: Optional[str] = None
    filter_capacitance: Optional[str] = None
    threshold_high: Optional[str] = None
    threshold_low: Optional[str] = None
    input_signal: Optional[str] = None
    resistor_value: Optional[str] = None
    led_current: Optional[str] = None
    input_ac: Optional[str] = None
    reference_voltage: Optional[str] = None

    @model_validator(mode='after')
    def validate_circuit_type(self):
        supported_types = {
            "buck_converter",
            "ldo_regulator",
            "inverting_amplifier",
            "noninverting_amplifier",
            "voltage_divider",
            "low_pass_filter",
            "high_pass_filter",
            "555_timer_astable",
            "bridge_rectifier",
            "voltage_multiplier",
            "comparator",
            "comparator_noninverting",
            "led_blinker_555",
            "microcontroller_board",
            "astable_multivibrator"
        }
        if self.circuit_type not in supported_types:
            raise ValueError(f"Unsupported circuit_type: {self.circuit_type}")
        return self

def call_gemini_for_spec(prompt: str) -> CircuitSpec:
    # Compose the system message
    SYSTEM_PROMPT = """You are a hardware design assistant. Extract exactly these fields from the user's prompt.
Supported circuit_type values (choose one):
- buck_converter
- ldo_regulator
- inverting_amplifier
- noninverting_amplifier
- voltage_divider
- low_pass_filter
- high_pass_filter
- 555_timer_astable
- bridge_rectifier
- voltage_multiplier
- comparator
- comparator_noninverting
- led_blinker_555
- microcontroller_board
- astable_multivibrator

Output the following JSON schema:

{
  "circuit_type": "<string>",
  "input_voltage": "<string or null>",
  "output_voltage": "<string or null>",
  "output_current": "<string or null>",
  "gain": "<string or null>",
  "mcu": "<string or null>",
  "sensor": "<string or null>",
  "clock_freq": "<string or null>",
  "Vin": "<string or null>",
  "Vout": "<string or null>",
  "cutoff_frequency": "<string or null>",
  "frequency": "<string or null>",
  "filter_capacitance": "<string or null>",
  "threshold_high": "<string or null>",
  "threshold_low": "<string or null>",
  "input_signal": "<string or null>",
  "resistor_value": "<string or null>",
  "led_current": "<string or null>",
  "input_ac": "<string or null>",
  "reference_voltage": "<string or null>"
}

Only return valid JSON. Set any irrelevant fields to null. Do not add explanations."""

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": SYSTEM_PROMPT + "\n\nUser Prompt: " + prompt
                    }
                ]
            }
        ]
    }

    params = {"key": GEMINI_API_KEY}

    print(">>> Gemini payload:", json.dumps(payload, indent=2))

    response = requests.post(GEMINI_API_URL, headers=headers, json=payload, params=params)
    print(">>> Gemini status:", response.status_code)
    print(">>> Gemini response:", response.text)

    if response.status_code != 200:
        raise Exception(f"Gemini API error {response.status_code}: {response.text}")

    try:
        content_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise Exception(f"Invalid Gemini response: {e}")

    print(">>> Gemini content (raw):", content_text)

    # Strip markdown code block if present
    if content_text.startswith("```"):
        content_text = content_text.strip("```").strip()
        if content_text.startswith("json"):
            content_text = content_text[len("json"):].strip()

    print(">>> Gemini content (cleaned):", content_text)

    try:
        spec = CircuitSpec.parse_raw(content_text)
        return spec
    except Exception as e:
        raise Exception(f"Failed to parse JSON:\n{content_text}\nError: {e}")
