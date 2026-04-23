#!/usr/bin/env python3
"""
Run nlp_100_20 eval with OpenAI: solve the same problem with polite and strict prompts,
save outputs in JSON format for comparison with baseline.
Requires: pip install requests pyyaml
Set OPENAI_API_KEY in env or .env file.

Style resolution (per-instance):
  - If prompts/polite_generic.txt exists AND the instance has an entry in manifest.yaml,
    the generic template is used with N_VARS and N_CONSTRAINTS substituted from the manifest.
  - Otherwise falls back to prompts/polite.txt / prompts/strict.txt.
  - Output filenames always use the base label (polite/strict), not polite_generic/strict_generic.
"""
import json
import os
import re
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = EVAL_DIR / "prompts"
PROBLEMS_DIR = EVAL_DIR / "problems"
OUTPUTS_DIR = EVAL_DIR / "outputs"
MANIFEST_PATH = PROBLEMS_DIR / "manifest.yaml"


def load_problem(instance_id: str = "instance_01") -> str:
    path = PROBLEMS_DIR / f"{instance_id}.txt"
    return path.read_text().strip()


def load_manifest() -> dict:
    """Return {instance_id: {n_vars, n_constraints}} from manifest.yaml, or {}."""
    if not MANIFEST_PATH.exists():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    data = yaml.safe_load(MANIFEST_PATH.read_text())
    return {e["id"]: e for e in data.get("instances", [])}


def load_prompt(style: str) -> str:
    return (PROMPTS_DIR / f"{style}.txt").read_text().strip()


def build_prompt(style: str, problem_spec: str, n_vars: int = None, n_constraints: int = None) -> str:
    """Build prompt, preferring _generic template when available and dimensions are known."""
    generic_path = PROMPTS_DIR / f"{style}_generic.txt"
    if generic_path.exists() and n_vars is not None and n_constraints is not None:
        template = generic_path.read_text().strip()
        template = template.replace("N_VARS", str(n_vars)).replace("N_CONSTRAINTS", str(n_constraints))
        return template.replace("{{PROBLEM_SPEC}}", problem_spec)
    return load_prompt(style).replace("{{PROBLEM_SPEC}}", problem_spec)


def extract_json(raw: str) -> str | None:
    """Extract JSON from response, handling markdown code blocks."""
    raw = raw.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if m:
        return m.group(1).strip()
    if raw.startswith("{"):
        return raw
    return None


def _load_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    env_path = EVAL_DIR.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise ValueError("Set OPENAI_API_KEY in environment or .env")


def run_openai(prompt: str, model: str = "gpt-4o-mini", max_tokens: int = 8192) -> str:
    key = _load_api_key()
    try:
        import requests
    except ImportError:
        raise ImportError("pip install requests")
    for attempt in range(3):
        try:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "max_tokens": max_tokens,
                },
                timeout=120,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"].get("content") or ""
        except Exception as e:
            if attempt == 2:
                raise
            import time
            time.sleep(5)
    return ""


def run_eval(instance_id: str = "instance_01", model: str = "gpt-4o-mini") -> dict:
    problem = load_problem(instance_id)
    manifest = load_manifest()
    meta = manifest.get(instance_id, {})
    n_vars = meta.get("n_vars")
    n_constraints = meta.get("n_constraints")
    OUTPUTS_DIR.mkdir(exist_ok=True)
    results = {}
    for style in ("polite", "strict"):
        prompt = build_prompt(style, problem, n_vars=n_vars, n_constraints=n_constraints)
        raw = run_openai(prompt, model=model)
        json_str = extract_json(raw) or raw
        out_path = OUTPUTS_DIR / f"{instance_id}_{style}_output.json"
        try:
            data = json.loads(json_str)
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
