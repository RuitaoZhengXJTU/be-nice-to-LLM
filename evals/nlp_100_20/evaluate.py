#!/usr/bin/env python3
"""
Example eval script for nlp_100_20: load task spec, build prompts (polite vs strict),
and run checks on model output. Replace run_agent() with your actual model call.
"""
import json
import yaml
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = EVAL_DIR / "prompts"
SPEC_PATH = EVAL_DIR / "task_spec.yaml"


def load_spec():
    with open(SPEC_PATH) as f:
        return yaml.safe_load(f)


def load_prompt(style: str) -> str:
    path = PROMPTS_DIR / f"{style}.txt"
    return path.read_text().strip()


def build_prompt(style: str, problem_spec: str) -> str:
    template = load_prompt(style)
    return template.replace("{{PROBLEM_SPEC}}", problem_spec)


def get_example_problem_spec() -> str:
    """Minimal NLP problem spec (100 vars, 20 constraints) for testing."""
    return (
        "minimize sum(x[i]^2 for i in 1..100)\n"
        "subject to: for j in 1..20: sum(x[i] for i in 1..100) >= 0 (example constraints).\n"
        "Bounds: -10 <= x[i] <= 10 for all i."
    )


def run_agent(prompt: str) -> str:
    """Stub: replace with actual LLM/agent call. Returns raw response text."""
    # TODO: call your agent (e.g. OpenAI, local model) with prompt; return response
    return ""


def check_instruction_following(raw: str, spec: dict) -> tuple[bool, str]:
    """Check output is valid JSON with required keys and dimensions."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    req = spec["output_format"]["required_keys"]
    for key in req:
        if key not in data:
            return False, f"Missing key: {key}"
    if "x" in data:
        if len(data["x"]) != spec["output_format"]["x_length"]:
            return False, f"x length {len(data['x'])} != {spec['output_format']['x_length']}"
    if "objective_value" in data and not isinstance(data["objective_value"], (int, float)):
        return False, "objective_value must be numeric"
    return True, "ok"


def run_eval(style: str, problem_spec: str | None = None):
    spec = load_spec()
    problem_spec = problem_spec or get_example_problem_spec()
    prompt = build_prompt(style, problem_spec)
    raw = run_agent(prompt)
    ok, msg = check_instruction_following(raw, spec)
    return {"style": style, "instruction_following_ok": ok, "message": msg, "raw_preview": raw[:200]}


if __name__ == "__main__":
    import sys
    style = (sys.argv[1] or "polite").lower()
    if style not in ("polite", "strict"):
        print("Usage: python evaluate.py [polite|strict]")
        sys.exit(1)
    result = run_eval(style)
    print(json.dumps(result, indent=2))
