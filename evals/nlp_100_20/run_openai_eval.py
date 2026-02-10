#!/usr/bin/env python3
"""
Run nlp_100_20 eval with OpenAI: solve the same problem with polite and strict prompts,
save outputs in JSON format for comparison with baseline.
Requires: pip install openai
Set OPENAI_API_KEY in env.
"""
import json
import os
import re
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = EVAL_DIR / "prompts"
PROBLEMS_DIR = EVAL_DIR / "problems"
OUTPUTS_DIR = EVAL_DIR / "outputs"


def load_problem(instance_id: str = "instance_01") -> str:
    path = PROBLEMS_DIR / f"{instance_id}.txt"
    return path.read_text().strip()


def load_prompt(style: str) -> str:
    return (PROMPTS_DIR / f"{style}.txt").read_text().strip()


def build_prompt(style: str, problem_spec: str) -> str:
    return load_prompt(style).replace("{{PROBLEM_SPEC}}", problem_spec)


def extract_json(raw: str) -> str | None:
    """Extract JSON from response, handling markdown code blocks."""
    raw = raw.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if m:
        return m.group(1).strip()
    # Try parsing whole response
    if raw.startswith("{"):
        return raw
    return None


def run_openai(prompt: str, model: str = "gpt-4o-mini") -> str:
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("pip install openai")
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("Set OPENAI_API_KEY in environment")
    client = OpenAI(api_key=key)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return resp.choices[0].message.content or ""


def run_eval(instance_id: str = "instance_01", model: str = "gpt-4o-mini") -> dict:
    problem = load_problem(instance_id)
    OUTPUTS_DIR.mkdir(exist_ok=True)
    results = {}
    for style in ("polite", "strict"):
        prompt = build_prompt(style, problem)
        raw = run_openai(prompt, model=model)
        json_str = extract_json(raw) or raw
        out_path = OUTPUTS_DIR / f"{instance_id}_{style}_output.json"
        try:
            data = json.loads(json_str)
            # Ensure required format
            if "x" in data and "objective_value" in data:
                with open(out_path, "w") as f:
                    json.dump(data, f, indent=2)
                results[style] = {"path": str(out_path), "valid": True}
            else:
                with open(out_path, "w") as f:
                    f.write(raw)
                results[style] = {"path": str(out_path), "valid": False, "error": "missing keys"}
        except json.JSONDecodeError as e:
            with open(out_path, "w") as f:
                f.write(raw)
            results[style] = {"path": str(out_path), "valid": False, "error": str(e)}
    return results


if __name__ == "__main__":
    import sys
    instance = sys.argv[1] if len(sys.argv) > 1 else "instance_01"
    model = sys.argv[2] if len(sys.argv) > 2 else "gpt-4o-mini"
    r = run_eval(instance, model)
    print(json.dumps(r, indent=2))
