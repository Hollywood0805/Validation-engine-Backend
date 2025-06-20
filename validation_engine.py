import os
import json
import re
from typing import Dict, List, Any, Generator, Tuple
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import concurrent.futures

# === Load OpenAI Client ===
load_dotenv(".env")
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in environment variables or .env file")

client = OpenAI(api_key=api_key)

# === Utility Paths ===
def get_rule_base_path(sub_path: str = "") -> Path:
    return (Path(__file__).parent / "rule_set" / sub_path).resolve()

def load_reference_file(form_name: str) -> str:
    txt_path = get_rule_base_path(f"generated_rules_editchecks/{form_name}.txt")
    if not txt_path.exists():
        raise FileNotFoundError(f"Reference TXT not found: {txt_path}")
    with open(txt_path, "r", encoding="utf-8") as f:
        return f.read()

# === NLP to JSON Conversion ===
def convert_nl_to_structured_json(nl_input: str, reference_text: str) -> Dict[str, Any]:
    prompt = f"""
You are a clinical trial form assistant.
Your task is to convert the following natural language input into a structured JSON format that matches the structure suggested by the reference rules.

Natural Language Input:
{nl_input}

Reference rules and context:
{reference_text}

Now output a JSON that follows the implied structure from the reference rules and fills in values using the natural language input.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r"^```json|```$", "", content).strip()
        return json.loads(content)
    except Exception as e:
        print(f"\u274c Error during NL-to-JSON conversion: {str(e)}")
        return {}

# === Rule Matching and Evaluation ===
def extract_rule_structure() -> Dict[str, List[str]]:
    rules_structure = {}
    base = get_rule_base_path()
    for folder in base.iterdir():
        if folder.is_dir():
            rules_structure[folder.name] = [file.stem for file in folder.glob("*.txt") if file.is_file()]
    return rules_structure

def find_all_matching_rule_files(form_name: str, rules_structure: Dict[str, List[str]]) -> List[Path]:
    form_normalized = re.sub(r'[\s_?]', '', form_name.lower())
    base = get_rule_base_path()
    matched_files = []
    for category, filenames in rules_structure.items():
        for fname in filenames:
            fname_normalized = re.sub(r'[\s_?]', '', fname.lower())
            if form_normalized in fname_normalized or fname_normalized in form_normalized:
                matched_files.append(base / category / f"{fname}.txt")
    return matched_files

def extract_exactly_matching_rules(file_paths: List[Path], user_json: Dict[str, Any]) -> List[str]:
    exact_matches = []
    target_form = re.sub(r'[\s_?]', '', user_json.get("form", "").lower())
    if not target_form:
        return exact_matches

    rule_block_pattern = re.compile(r'(rule\s+\".+?\"\s*\{.*?\})', re.DOTALL | re.IGNORECASE)
    form_cond_pattern = re.compile(r'form\s*==\s*\"(.+?)\"', re.IGNORECASE)

    for file_path in file_paths:
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8")
        rule_blocks = rule_block_pattern.findall(content)
        for block in rule_blocks:
            m = form_cond_pattern.search(block)
            if not m:
                continue
            form_in_rule = re.sub(r'[\s_?]', '', m.group(1).lower())
            if form_in_rule == target_form:
                exact_matches.append(block.strip())

    return exact_matches

def validate_rules_with_openai_stream(user_json: Dict[str, Any], matched_rules: List[str]) -> Generator[str, None, None]:
    user_data_pretty = json.dumps(user_json, indent=2)
    rules_str = "\n".join(matched_rules)

    prompt = f"""
You are a clinical data validation assistant.

Given the following **form input data** in JSON format and a set of validation **rules**, do the following:
1. Identify the best matched rules from the list.
2. For each applicable rule, apply it to the user data.
If the User Data Contradicts with the Rule, i.e if the fields have conflicting values, mark it as Failed. If the User Data is Valid according to the Rule, mark it as Validated. If the Rule does not apply to the User Data, mark it as Not Applicable.
3. Give an introduction:
> What is the user trying to do?
> What is the form name in normal text?
> What is the user data in proper format?
> What is the user's goal in normal text?
> What is the user's expected outcome in normal text?

4. Output a structured validation report for each rule in this format:

### Rule: <Rule Name>
**Status**: Validated / Failed / Not Applicable  ✅ ❌ ⚠️
**Reason**: Detailed explanation
**Action**: Suggested follow-up

Format clearly using markdown.

---
### Form Data:
{user_data_pretty}

---
### Rules:
{rules_str}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            stream=True
        )
        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except Exception as e:
        yield f"\n\u274c Error from OpenAI: {str(e)}"

# === API Entry Point ===
def get_rule_summary(user_json: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    rules_structure = extract_rule_structure()
    rule_files = find_all_matching_rule_files(user_json.get("form", ""), rules_structure)
    exact_rules = extract_exactly_matching_rules(rule_files, user_json)
    rule_names = [re.search(r'rule\s+\"(.+?)\"', r, re.IGNORECASE).group(1) if re.search(r'rule\s+\"(.+?)\"', r, re.IGNORECASE) else "Unnamed Rule" for r in exact_rules]
    return rule_names, exact_rules

def stream_validation_engine(user_json: Dict[str, Any]) -> Generator[str, None, None]:
    _, matched_rules = get_rule_summary(user_json)
    if not matched_rules:
        yield "\u26a0\ufe0f No matching rules found for this form.\n"
    else:
        yield from validate_rules_with_openai_stream(user_json, matched_rules)

# === CLI Entry ===
if __name__ == "__main__":
    form_name = input("Enter form name (e.g., Demography):\n> ").strip()
    try:
        reference_text = load_reference_file(form_name)
    except FileNotFoundError as e:
        print(f"\u274c {str(e)}")
        exit(1)

    nl_input = input("\nEnter clinical form input (natural language):\n> ")
    user_json = convert_nl_to_structured_json(nl_input, reference_text)

    print("\n[INFO] Reconstructed structured JSON data:")
    print(json.dumps(user_json, indent=2))

    print("\n[INFO] Validation report streaming:\n")
    for chunk in stream_validation_engine(user_json):
        print(chunk, end="", flush=True)
