"""Handles redaction of sensitive data."""

import json

from .config import LOG_UNREDACTED_DATA

REDACT_KEYS = ["inputVariables", "participant", "variables"]


def dict_redact(data: dict) -> dict:
    """Recursively redacts a dictionary.

    Args:
        data: The dictionary to redact.

    Returns:
        The redacted dictionary.
    """
    for key, value in data.items():
        if key in REDACT_KEYS:
            data[key] = "<REDACTED>"
        elif isinstance(value, dict):
            data[key] = dict_redact(value)
        elif isinstance(value, list):
            data[key] = [dict_redact(item) if isinstance(item, dict) else item for item in value]
    return data


def redact(data: str | dict) -> str | dict:
    """Redacts the given data if LOG_UNREDACTED_DATA is not true.

    If the data is a dictionary, it is passed to dict_redact.
    If the data is a JSON string that deserializes to a dictionary, it
    is passed to dict_redact.

    Args:
        data: The data (string or dictionary) to redact.

    Returns:
        The redacted data (string or dictionary).
    """
    if LOG_UNREDACTED_DATA == 'true':
        return data

    if isinstance(data, dict):
        return dict_redact(data)

    try:
        json_data = json.loads(data)
        if isinstance(json_data, dict):
            return json.dumps(dict_redact(json_data))
    except json.JSONDecodeError:
        pass

    return '<REDACTED>'
