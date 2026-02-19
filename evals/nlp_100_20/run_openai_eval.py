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
MANIFEST_PATH = PROBLEMS_DIR / "problem_manifest.yaml"


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}
    import yaml
    with open(MANIFEST_PATH) as f:
        return yaml.safe_load(f) or {}


def load_problem(instance_id: str = "instance_01") -> str:
    path = PROBLEMS_DIR / f"{instance_id}.txt"
    return path.read_text().strip()


def load_prompt(style: str) -> str:
    return (PROMPTS_DIR / f"{style}.txt").read_text().strip()


def build_prompt(style: str, problem_spec: str, n_vars: int = 100, n_constraints: int = 20) -> str:
    t = load_prompt(style)
    t = t.replace("{{N_VARS}}", str(n_vars)).replace("{{N_CONSTRAINTS}}", str(n_constraints))
    return t.replace("{{PROBLEM_SPEC}}", problem_spec)


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


def run_openai(prompt: str, model: str = "gpt-4o-mini") -> str:
    key = _load_api_key()
    try:
        import requests
    except ImportError:
        raise ImportError("pip install requests")
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0},
        timeout=240,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"].get("content") or ""


def run_eval(instance_id: str = "instance_01", model: str = "gpt-4o-mini") -> dict:
    manifest = load_manifest()
    meta = manifest.get(instance_id, {})
    n_vars = meta.get("n_variables", 100)
    n_constraints = meta.get("n_constraints", 20)
    problem = load_problem(instance_id)
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
                if len(data["x"]) != n_vars:
                    with open(out_path, "w") as f:
                        f.write(raw)
                    results[style] = {"path": str(out_path), "valid": False, "error": f"x length {len(data['x'])} != {n_vars}"}
                else:
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
    if instance.lower() == "all":
        manifest = load_manifest()
        ids = sorted(manifest.keys()) if manifest else ["instance_01", "instance_02", "instance_03"]
        all_results = {}
        for iid in ids:
            all_results[iid] = run_eval(iid, model)
        print(json.dumps(all_results, indent=2))
    else:
        r = run_eval(instance, model)
        print(json.dumps(r, indent=2))
