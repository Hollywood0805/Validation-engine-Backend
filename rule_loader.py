import os
import json

def load_rules(rule_keys, rules_dir="rules"):
    rules = {}
    for key in rule_keys:
        file_path = os.path.join(rules_dir, f"{key}.json")
        try:
            with open(file_path, "r") as f:
                rules[key] = json.load(f)
        except FileNotFoundError:
            print(f"⚠️ Warning: No rule file found for key '{key}'")
    return rules
