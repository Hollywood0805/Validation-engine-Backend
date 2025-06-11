import os

# Base directory for rule JSON files extracted from rule_set.zip
BASE_RULE_PATH = os.path.join(
    os.path.dirname(__file__),
    "rule_set",
    "generated_rules_editchecks"
)

# OpenAI API Key (recommended: use environment variable or .env loader)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-your-openai-api-key")