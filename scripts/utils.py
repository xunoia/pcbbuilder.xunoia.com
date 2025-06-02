# scripts/utils.py

import os
import json
from pathlib import Path
from typing import Any, Dict

def load_json(filepath: str) -> Dict[str, Any]:
    """
    Load a JSON file from disk and return it as a Python dict.
    Raises FileNotFoundError if it doesn’t exist.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {filepath}")
    return json.loads(path.read_text())

def save_json(data: Any, filepath: str) -> None:
    """
    Save a Python object (dict/list/etc.) as a JSON file with indentation.
    """
    Path(filepath).write_text(json.dumps(data, indent=2))

def replace_placeholders(obj: Any, values: Dict[str, str]) -> Any:
    """
    Recursively replace placeholders in strings (e.g., "{input_voltage}") 
    with values from the `values` dict.
    Works on nested dicts, lists, and strings.
    """
    if isinstance(obj, str):
        # Replace all occurrences of {key} with values[key]
        def repl(match):
            key = match.group(1)
            return values.get(key, match.group(0))
        import re
        return re.sub(r"\{([^}]+)\}", repl, obj)
    elif isinstance(obj, dict):
        return {k: replace_placeholders(v, values) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_placeholders(item, values) for item in obj]
    else:
        return obj

def ensure_folder(path: str) -> None:
    """
    Create a folder (and parents) if it doesn’t exist.
    """
    Path(path).mkdir(parents=True, exist_ok=True)
