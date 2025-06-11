print("rule_mapper module loaded")

def map_rule_categories(data):
    categories = []
    if 'age' in data or 'dob' in data:
        categories.append('demographics')
    if 'height_cm' in data or 'weight_kg' in data:
        categories.append('vitals')
    if 'EVAL_abd' in data or 'EVAL_chest' in data:
        categories.append('physical_examination')
    if 'hematology_date' in data:
        categories.append('hematology')
    return categories
