# backend/ai_validator.py

def validate_with_ai(data, rules):
    """
    Dummy validation function that always returns a pass for testing.
    Replace with your AI validation logic later.
    """
    validation_results = []
    for field in data:
        validation_results.append({
            "field": field,
            "status": "PASS",
            "reason": "Validated successfully (stub)"
        })
    return validation_results
