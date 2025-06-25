import os
import json
import re
from typing import Dict, List, Any, Generator, Tuple
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# === Load OpenAI Client ===
load_dotenv(".env")
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in environment variables or .env file")

client = OpenAI(api_key=api_key)

# === Alias map for robust form matching ===
FORM_ALIASES = {
    # Core forms
    "adverseevent": "adverse event",
    "adverseeventlog": "adverse event log",
    "inclusioncriteria": "inclusion/exclusion",
    "exclusioncriteria": "inclusion/exclusion",
    "inclusionexclusion": "inclusion/exclusion",
    "inclusionexclusioncriteria": "inclusion/exclusion",
    "inclusion/exclusion": "inclusion/exclusion",
    "pharmacokinetics": "pharmacokinetics",
    "demography": "demography",
    "pregnancy": "pregnancy",
    "informedconsent": "informedconsent",

    # Additions for better matching (safe)
    "hematology": "hematologyinlabs",
    "hematologyinlabs": "hematologyinlabs"
}

def normalize_form_name(name: str) -> str:
    normalized = re.sub(r'[^\w]', '', name.lower().strip())
    return FORM_ALIASES.get(normalized, normalized)

def normalize_file_stem(stem: str) -> str:
    stem_norm = re.sub(r'[^\w]', '', stem.lower())
    return FORM_ALIASES.get(stem_norm, stem_norm)

# === Utility Paths ===
def get_rule_base_path(sub_path: str = "") -> Path:
    return (Path(__file__).parent / "rule_set" / sub_path).resolve()

def load_reference_file(form_name: str) -> str:
    base_path = Path(__file__).parent / "rule_set"
    folders_to_search = [
        "generated_rules_derivations",
        "generated_rules_editchecks",
        "generated_rules_protocol",
    ]

    def normalize_name(name: str) -> str:
        return re.sub(r'[^a-z0-9]', '', name.lower())

    norm_form = normalize_name(form_name)

    combined_content = []
    for folder in folders_to_search:
        folder_path = base_path / folder
        if not folder_path.exists():
            continue
        for file_path in folder_path.glob("*.txt"):
            norm_file = normalize_name(file_path.stem)
            if norm_form == norm_file:
                with open(file_path, "r", encoding="utf-8") as f:
                    combined_content.append(f.read())

    if not combined_content:
        raise FileNotFoundError(f"Reference TXT not found for form '{form_name}' in any rule folders.")
    return "\n\n".join(combined_content)

def convert_nl_to_structured_json(nl_input: str, reference_text: str, form_name: str) -> Dict[str, Any]:
    prompt = f"""
You are a clinical trial form assistant.
Convert the following natural language input into a structured JSON format used for rule-based validation.
Strictly follow this JSON format:
{{
  "form": "{form_name}",
  "recordPosition": 0,
  "fields": {{
    "<field_name>": <value or null>
  }}
}}
Natural Language Input:
{nl_input}
Reference Rules:
{reference_text}
Output only valid JSON. No comments.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r"^```json|```$", "", content).strip()
        return json.loads(content)
    except Exception as e:
        print(f"❌ Error during NL-to-JSON conversion: {str(e)}")
        return {}

def extract_rule_structure() -> Dict[str, List[str]]:
    rules_structure = {}
    base = get_rule_base_path()
    for folder in base.iterdir():
        if folder.is_dir():
            rules_structure[folder.name] = [file.stem for file in folder.glob("*.txt") if file.is_file()]
    return rules_structure

def find_all_matching_rule_files(form_name: str, rules_structure: Dict[str, List[str]]) -> List[Path]:
    form_normalized = normalize_form_name(form_name)
    base = get_rule_base_path()
    matched_files = []
    for category, filenames in rules_structure.items():
        for fname in filenames:
            fname_normalized = normalize_file_stem(fname)
            if (form_normalized in fname_normalized) or (fname_normalized in form_normalized):
                matched_files.append(base / category / f"{fname}.txt")
    return matched_files

def extract_exactly_matching_rules(file_paths: List[Path], user_json: Dict[str, Any]) -> List[Tuple[str, str]]:
    exact_matches = []
    user_form_raw = user_json.get("form", "")
    user_form = normalize_form_name(user_form_raw)
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
            rule_form_raw = m.group(1)
            rule_form = normalize_form_name(rule_form_raw)
            print(f"DEBUG: User form normalized: {user_form}, Rule form normalized: {rule_form}")
            if user_form == rule_form:
                exact_matches.append((block.strip(), file_path.parent.name))
    return exact_matches

def validate_rules_with_openai_stream(user_data: Dict[str, Any], matched_rules: List[Tuple[str, str]]) -> Generator[str, None, None]:
    user_data_pretty = json.dumps(user_data, indent=2)
    rules_combined = "\n\n".join([r[0] for r in matched_rules])
    prompt = f"""
You are a clinical data validation assistant.
Given form input data and a set of rules:
- Provide a goal-oriented introduction
- Validate each rule:
    - Rule Name
    - Folder
    - Status ✅ ❌ ⚠️
    - Reason
    - Action (if applicable)

### Form Data:
{user_data_pretty}

### Rules:
{rules_combined}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            stream=True
        )
        for chunk in response:
            content = getattr(chunk.choices[0].delta, "content", None)
            if content:
                yield content
    except Exception as e:
        yield f"\n❌ Error from OpenAI: {str(e)}"

def get_rule_summary(user_json: Dict[str, Any]) -> Tuple[List[str], List[Tuple[str, str]]]:
    rules_structure = extract_rule_structure()
    rule_files = find_all_matching_rule_files(user_json.get("form", ""), rules_structure)
    exact_rules = extract_exactly_matching_rules(rule_files, user_json)
    rule_names = [
        re.search(r'rule\s+\"(.+?)\"', r[0], re.IGNORECASE).group(1)
        if re.search(r'rule\s+\"(.+?)\"', r[0], re.IGNORECASE)
        else "Unnamed Rule"
        for r in exact_rules
    ]
    return rule_names, exact_rules

def stream_validation_engine(user_json: Dict[str, Any]) -> Generator[str, None, None]:
    _, matched_rules = get_rule_summary(user_json)
    if not matched_rules:
        yield "⚠️ No matching rules found for this form.\n"
    else:
        yield from validate_rules_with_openai_stream(user_json, matched_rules)

# === CLI Interface ===
if __name__ == "__main__":
    form_name = input("Enter form name (e.g., Demography):\n> ").strip()
    print(f"[DEBUG] Normalized form name: {normalize_form_name(form_name)}")
    try:
        reference_text = load_reference_file(form_name)
    except FileNotFoundError as e:
        print(f"❌ {str(e)}")
        exit(1)

    nl_input = input("\nEnter clinical form input (natural language):\n> ")
    user_json = convert_nl_to_structured_json(nl_input, reference_text, form_name)

    print("\n[INFO] Reconstructed structured JSON data:")
    print(json.dumps(user_json, indent=2))

    print("\n[INFO] Validation report streaming:\n")
    for chunk in stream_validation_engine(user_json):
        print(chunk, end="", flush=True)
