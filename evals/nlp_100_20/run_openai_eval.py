#!/usr/bin/env python3
"""
Run nlp_100_20 eval with gpt-4o-mini: solve instances with polite and strict prompts,
save raw outputs in JSON format.

Without --seed the original unsuffixed naming (<instance>_<style>_output.json) is used
so the baseline files are not overwritten.
With --seed N outputs are saved as <instance>_<style>_seed<N>_output.json.

Output schema per file:
  {
    "instance_id":      str,
    "style":            "polite" | "strict",
    "model":            str,
    "seed":             int | null,
    "finish_reason":    str | null,
    "raw_text":         str | null,
    "error":            str | null
  }

Does NOT score outputs. Stay out of run_aggregate.py and baseline_pyomo.py.
Requires: pip install requests
Set OPENAI_API_KEY in env or a .env file two directories up.
"""
import json
import os
import re
import time
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = EVAL_DIR / "prompts"
PROBLEMS_DIR = EVAL_DIR / "problems"
OUTPUTS_DIR = EVAL_DIR / "outputs"

MODEL = "gpt-4o-mini"
TEMPERATURE = 0
MAX_TOKENS = 16384
STYLES = ("polite", "strict")

# instances currently in aggregate (07 and 10 excluded under truncation rule)
DEFAULT_INSTANCES = [
    "instance_01", "instance_02", "instance_03", "instance_04",
    "instance_05", "instance_06", "instance_08", "instance_09",
]


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


def load_problem(instance_id: str) -> str:
    return (PROBLEMS_DIR / f"{instance_id}.txt").read_text().strip()


def load_prompt(style: str) -> str:
    return (PROMPTS_DIR / f"{style}.txt").read_text().strip()


def build_prompt(style: str, problem_spec: str) -> str:
    return load_prompt(style).replace("{{PROBLEM_SPEC}}", problem_spec)


def extract_json(raw: str):
    """Extract and parse JSON from raw model output. Returns dict or None."""
    if not raw:
        return None
    raw = raw.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if m:
        candidate = m.group(1).strip()
    elif raw.startswith("{"):
        candidate = raw
    else:
        m2 = re.search(r"\{[\s\S]*\}", raw)
        candidate = m2.group(0) if m2 else None
    if not candidate:
        return None
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def call_openai(
    prompt: str,
    model: str = MODEL,
    temperature: int = TEMPERATURE,
    max_tokens: int = MAX_TOKENS,
    seed: int = None,
) -> tuple:
    """
    Call the OpenAI Chat Completions API (text-only).
    Returns (raw_text, finish_reason, error_string).
    On success, error_string is None. On failure, raw_text is None.

    seed: integer passed to the API 'seed' field for reproducibility.
          None means omit the field (default API behaviour).
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
        "messages": [{"role": "user", "content": prompt}],
    }
    if seed is not None:
        payload["seed"] = seed

    for attempt in range(3):
        try:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=180,
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


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------

def run_eval(
    instances=None,
    styles=STYLES,
    model=MODEL,
    seed: int = None,
):
    """
    Run the eval loop over the given instances and styles.

    seed: when provided, output filenames use the seed-suffixed convention
          (<instance>_<style>_seed<N>_output.json) so they do not overwrite
          the original unsuffixed baseline files.
    """
    OUTPUTS_DIR.mkdir(exist_ok=True)

    if instances is None:
        instances = DEFAULT_INSTANCES

    results = {}
    total = len(instances) * len(styles)
    done = 0

    for inst_id in instances:
        problem = load_problem(inst_id)

        for style in styles:
            done += 1
            seed_tag = f" seed={seed}" if seed is not None else ""
            print(f"[{done}/{total}] {inst_id} / {style}{seed_tag} ...", flush=True)

            prompt = build_prompt(style, problem)
            raw_text, finish_reason, error = call_openai(
                prompt, model=model, seed=seed
            )

            output = {
                "instance_id": inst_id,
                "style": style,
                "model": model,
                "seed": seed,
                "finish_reason": finish_reason,
                "raw_text": raw_text,
                "error": error,
            }

            if seed is not None:
                out_path = OUTPUTS_DIR / f"{inst_id}_{style}_seed{seed}_output.json"
            else:
                out_path = OUTPUTS_DIR / f"{inst_id}_{style}_output.json"

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=True)

            status = "ERROR" if error else "OK"
            parsed = extract_json(raw_text) if raw_text else None
            json_shaped = "JSON" if parsed is not None else "no-JSON"
            trunc = " TRUNCATED" if finish_reason == "length" else ""
            print(f"  -> {status} | finish={finish_reason}{trunc} | {json_shaped}")

            key = f"{inst_id}_{style}" + (f"_seed{seed}" if seed is not None else "")
            results[key] = {
                "status": status,
                "finish_reason": finish_reason,
                "json_shaped": parsed is not None,
            }

    return results


def summarize(results: dict, seed=None):
    suffix = f"_seed{seed}" if seed is not None else ""
    for style in STYLES:
        keys = [k for k in results if k.endswith(f"_{style}{suffix}")]
        total = len(keys)
        json_count = sum(1 for k in keys if results[k]["json_shaped"])
        trunc_count = sum(1 for k in keys if results[k]["finish_reason"] == "length")
        error_count = sum(1 for k in keys if results[k]["status"] == "ERROR")
        parts = [f"{style}: {json_count}/{total} JSON-shaped"]
        if trunc_count:
            parts.append(f"{trunc_count} truncated")
        if error_count:
            parts.append(f"{error_count} errors")
        print(", ".join(parts))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run nlp_100_20 eval with gpt-4o-mini."
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Integer seed for the OpenAI API 'seed' field. "
             "Output files will be named <instance>_<style>_seed<N>_output.json "
             "to avoid overwriting unsuffixed baseline files.",
    )
    parser.add_argument(
        "--instances", nargs="*", default=None,
        help="Subset of instance IDs to run (e.g. instance_01 instance_03). "
             "Default: all 8 in-aggregate instances (01-06, 08, 09).",
    )
    parser.add_argument(
        "--styles", nargs="*", default=list(STYLES),
        help="Prompt styles to run. Default: polite strict.",
    )
    parser.add_argument(
        "--model", default=MODEL,
        help=f"OpenAI model. Default: {MODEL}.",
    )
    args = parser.parse_args()

    instances = args.instances if args.instances else None

    results = run_eval(
        instances=instances,
        styles=args.styles,
        model=args.model,
        seed=args.seed,
    )
    print("\n=== Summary ===")
    summarize(results, seed=args.seed)
