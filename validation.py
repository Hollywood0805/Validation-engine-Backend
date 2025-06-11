from backend.extractor import extract_patient_data
from backend.rule_mapper import map_rule_categories
from backend.rule_loader import load_rules
from backend.ai_validator import validate_with_ai

def run_validation(input_text):
    print("Loading extractor.py...")
    data = extract_patient_data(input_text)
    
    # Get categories for rules based on extracted data
    rule_keys = map_rule_categories(data)
    
    # Load rules based on those categories
    rules = load_rules(rule_keys)
    
    # Run AI validation
    validation_results = validate_with_ai(data, rules)
    
    return {
        "structured_data": data,
        "validation_results": validation_results
    }


