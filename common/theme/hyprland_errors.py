"""Normalize Hyprland's plain and JSON configerrors without inventing errors."""
import json


def parse_config_errors(stdout):
    text = stdout.strip()
    if not text:
        return []
    try:
        value = json.loads(text)
    except ValueError:
        value = text
    if value is None or value == {}:
        return []
    values = value if isinstance(value, list) else [value]
    errors = []
    for value in values:
        message = value if isinstance(value, str) else json.dumps(value)
        errors.extend(line.strip() for line in message.splitlines() if line.strip())
    return errors
