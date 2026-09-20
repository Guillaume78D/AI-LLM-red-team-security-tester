import json
from pathlib import Path
from openai import OpenAI
import config

client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY, timeout=180)

TEST_CASES_PATH = Path(__file__).parent / "test_cases.json"

CATEGORY_LABELS = {
    "prompt_injection": "Prompt Injection",
    "instruction_conflict": "Instruction Conflict",
    "system_prompt_extraction": "System Prompt Extraction",
    "jailbreak": "Jailbreak Resistance",
    "sensitive_leakage": "Sensitive Information Leakage",
}


def load_test_cases(file_path=TEST_CASES_PATH):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_test(prompt, system_prompt=config.TARGET_SYSTEM_PROMPT):
    response = client.chat.completions.create(
        model=config.MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=config.TEMPERATURE,
    )
    return response.choices[0].message.content