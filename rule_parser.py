def extract_fields_from_rules(rules):
    """
    From loaded rules, extract the list of unique data fields
    that need to be extracted and validated.

    Assumes each rule has a 'fields' key listing involved data fields.
    Adjust based on your actual rule JSON schema.
    """
    fields = set()
    for rule in rules:
        # Example: rule['fields'] could be a list of field names
        rule_fields = rule.get("fields", [])
        for f in rule_fields:
            fields.add(f)
    return list(fields)


def extract_validation_conditions(rules):
    """
    Parse rules into a usable format for validation.

    Return a dict mapping field -> list of validation conditions.

    Each validation condition might be a dict describing the check,
    e.g., {"type": "range", "min": 0, "max": 120}
    
    This depends on your actual rule JSON structure.

    Example output:
    {
        "age": [{"type": "range", "min": 0, "max": 120}],
        "weight_kg": [{"type": "range", "min": 10, "max": 200}]
    }
    """
    validations = {}
    for rule in rules:
        fields = rule.get("fields", [])
        conditions = rule.get("conditions", [])
        for f in fields:
            if f not in validations:
                validations[f] = []
            validations[f].extend(conditions)
    return validations
