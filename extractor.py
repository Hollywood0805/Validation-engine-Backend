import re

def extract_fields_from_text(text: str, rule_definitions: list) -> dict:
    """
    Extracts field values from free-text input using patterns defined in rule_definitions.

    Parameters:
    - text: Unstructured user input (e.g., patient summary)
    - rule_definitions: List of rule dicts, each containing:
        {
            "field": "age",
            "pattern": r"age[:\s]*([0-9]{1,3})"
        }

    Returns:
    - Dictionary of {field_name: extracted_value}
    """

    extracted = {}

    for rule in rule_definitions:
        field = rule.get("field")
        pattern = rule.get("pattern")

        if not field or not pattern:
            continue  # Skip if missing required keys

        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw_val = match.group(1)
            # Try to auto-type
            try:
                if "." in raw_val:
                    value = float(raw_val)
                else:
                    value = int(raw_val)
            except ValueError:
                value = raw_val  # fallback to string
            extracted[field] = value

    return extracted

