#!/usr/bin/env python3
"""
Run image-recognition eval with gpt-4o-mini (vision input).

Loads all problem YAMLs from evals/imagerec/problems/, runs each problem under
both polite and strict prompt wrappers, and saves raw outputs to
evals/imagerec/outputs/<problem_id>_<style>_output.json.

Output schema per file:
  {
    "problem_id":    str,
    "style":         "polite" | "strict",
    "model":         str,
    "finish_reason": str | null,
    "raw_text":      str | null,
    "error":         str | null
  }

Does NOT score outputs. Does NOT touch grade_image.py. Scoring is Jeremy's lane.
Requires: pip install requests pyyaml
Set OPENAI_API_KEY in env or a .env file two directories up.
"""
import json
import os
import re
import time
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
PROBLEMS_DIR = EVAL_DIR / "problems"
PROMPTS_DIR = EVAL_DIR / "prompts"
OUTPUTS_DIR = EVAL_DIR / "outputs"

MODEL = "gpt-4o-mini"
TEMPERATURE = 0
# Vision outputs are tiny -- a few dozen tokens at most.
# Leaving max_tokens unset lets the API use its default (~4096), which is plenty.
MAX_TOKENS = 512

STYLES = ("polite", "strict")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    for candidate in [
        EVAL_DIR.parent.parent / ".env",
        EVAL_DIR.parent.parent.parent / ".env",
    ]:
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if line.startswith("OPENAI_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise ValueError("Set OPENAI_API_KEY in environment or .env")


def load_yaml_simple(path: Path) -> dict:
    """
    Minimal YAML loader (no dependency) for flat key: value files.
    Falls back to pyyaml if available.
    """
    try:
        import yaml
        return yaml.safe_load(path.read_text())
    except ImportError:
        pass
    data = {}
    for line in path.read_text().splitlines():
        if ":" in line and not line.strip().startswith("#"):
            k, _, v = line.partition(":")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            data[k] = v
    return data


def load_problems() -> list:
    """Return sorted list of problem dicts, excluding manifest.yaml."""
    yamls = sorted(
        f for f in PROBLEMS_DIR.glob("*.yaml") if f.stem != "manifest"
    )
    problems = []
    for yf in yamls:
        try:
            import yaml
            prob = yaml.safe_load(yf.read_text())
        except ImportError:
            prob = load_yaml_simple(yf)
        if prob and prob.get("id"):
            problems.append(prob)
    return problems


def load_prompt_template(style: str) -> str:
    """Load polite.txt or strict.txt from prompts/."""
    return (PROMPTS_DIR / f"{style}.txt").read_text()


def build_text_prompt(template: str, prob: dict) -> str:
    """
    Fill template slots from the problem YAML.
    Removes the 'Image: {{IMAGE_INPUT}}' line -- the image is provided as a
    vision content block in the API call, not embedded in the text.
    """
    text = template
    text = text.replace("{{TASK_TYPE}}", str(prob.get("task_type", "")))
    text = text.replace("{{QUESTION}}", str(prob.get("question", "")))
    text = text.replace("{{OUTPUT_FORMAT}}", str(prob.get("output_format", "")))
    # Remove the image reference line; image arrives via the vision content block
    text = re.sub(r"Image:\s*\{\{IMAGE_INPUT\}\}\s*\n?", "", text)
    return text.strip()


def call_openai_vision(
    text_prompt: str,
    image_url: str,
    model: str = MODEL,
    temperature: int = TEMPERATURE,
    max_tokens: int = MAX_TOKENS,
) -> tuple:
    """
    Call the OpenAI Chat Completions API with a vision (image_url) content block.
    Returns (raw_text, finish_reason, error_string).
    On success, error_string is None. On failure, raw_text is None.
    """
    try:
        import requests
    except ImportError:
        raise ImportError("pip install requests")

    key = _load_api_key()

    payload = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text_prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
    }

    for attempt in range(3):
        try:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=120,
            )
            r.raise_for_status()
            choice = r.json()["choices"][0]
            raw_text = choice["message"].get("content") or ""
            finish_reason = choice.get("finish_reason", "unknown")
            return raw_text, finish_reason, None
        except Exception as e:
            err = str(e)
            if attempt < 2:
                time.sleep(5)
            else:
                return None, None, err

    return None, None, "unknown error after retries"


def extract_json_from_text(raw: str):
    """
    Try to extract a JSON object from raw model output.
    Returns the parsed dict, or None if parsing fails.
    Does NOT raise.
    """
    if not raw:
        return None
    raw = raw.strip()
    # Prefer content inside a markdown code fence
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if m:
        candidate = m.group(1).strip()
    elif raw.startswith("{"):
        candidate = raw
    else:
        # Find first { ... } block
        m2 = re.search(r"\{[\s\S]*\}", raw)
        candidate = m2.group(0) if m2 else None
    if not candidate:
        return None
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------

def run_eval(problems=None, styles=STYLES, model=MODEL):
    OUTPUTS_DIR.mkdir(exist_ok=True)

    if problems is None:
        problems = load_problems()

    templates = {style: load_prompt_template(style) for style in styles}

    results = {}
    total = len(problems) * len(styles)
    done = 0

    for prob in problems:
        prob_id = prob["id"]
        image_url = prob.get("image_url", "").strip().strip('"').strip("'")

        for style in styles:
            done += 1
            print(f"[{done}/{total}] {prob_id} / {style} ...", flush=True)

            text_prompt = build_text_prompt(templates[style], prob)
            raw_text, finish_reason, error = call_openai_vision(
                text_prompt, image_url, model=model
            )

            output = {
                "problem_id": prob_id,
                "style": style,
                "model": model,
                "finish_reason": finish_reason,
                "raw_text": raw_text,
                "error": error,
            }

            out_path = OUTPUTS_DIR / f"{prob_id}_{style}_output.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=True)

            status = "ERROR" if error else "OK"
            parsed = extract_json_from_text(raw_text) if raw_text else None
            json_shaped = "JSON" if parsed is not None else "no-JSON"
            print(f"  -> {status} | finish={finish_reason} | {json_shaped}")

            results[f"{prob_id}_{style}"] = {
                "status": status,
                "finish_reason": finish_reason,
                "json_shaped": parsed is not None,
            }

    return results


def summarize(results: dict):
    """Print a quick per-style tally of JSON-shaped outputs."""
    for style in STYLES:
        keys = [k for k in results if k.endswith(f"_{style}")]
        total = len(keys)
        json_count = sum(1 for k in keys if results[k]["json_shaped"])
        error_count = sum(1 for k in keys if results[k]["status"] == "ERROR")
        print(
            f"{style}: {json_count}/{total} JSON-shaped"
            + (f", {error_count} errors" if error_count else "")
        )


if __name__ == "__main__":
    results = run_eval()
    print("\n=== Summary ===")
    summarize(results)
