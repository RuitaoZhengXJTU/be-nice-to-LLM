#!/usr/bin/env python3
"""
Compare agent outputs (polite vs strict) against Pyomo baseline.
Usage: python compare_results.py baseline_solution.json polite_output.json strict_output.json
"""
import json
import sys
from pathlib import Path


def load_json(path: str) -> dict | None:
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"  Load error: {e}")
        return None


def check_format(data: dict, n: int = 100) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "not a dict"
    if "x" not in data or "objective_value" not in data:
        return False, "missing x or objective_value"
    if len(data["x"]) != n:
        return False, f"x length {len(data['x'])} != {n}"
    if not isinstance(data["objective_value"], (int, float)):
        return False, "objective_value not numeric"
    return True, "ok"


def optimality_gap(obj_agent: float, obj_baseline: float, eps: float = 1e-8) -> float:
    denom = max(abs(obj_baseline), eps)
    return abs(obj_agent - obj_baseline) / denom


def compare(
    baseline_path: str,
    polite_path: str | None = None,
    strict_path: str | None = None,
    n: int = 100,
) -> dict:
    baseline = load_json(baseline_path)
    if not baseline:
        return {"error": f"Could not load baseline: {baseline_path}"}
    obj_ref = baseline.get("objective_value", 0.0)

    out = {
        "baseline_objective": obj_ref,
        "polite": None,
        "strict": None,
    }

    for name, path in [("polite", polite_path), ("strict", strict_path)]:
        if not path:
            continue
        data = load_json(path)
        if not data:
            out[name] = {"valid": False, "error": "load failed"}
            continue
        ok, msg = check_format(data, n)
        if not ok:
            out[name] = {"valid": False, "error": msg}
            continue
        obj = data["objective_value"]
        gap = optimality_gap(obj, obj_ref)
        out[name] = {
            "valid": True,
            "objective_value": obj,
            "optimality_gap": gap,
            "instruction_following": "ok",
        }

    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 1:
        print("Usage: python compare_results.py baseline.json [polite.json] [strict.json]")
        sys.exit(1)
    baseline = args[0]
    polite = args[1] if len(args) > 1 else None
    strict = args[2] if len(args) > 2 else None
    result = compare(baseline, polite, strict)
    print(json.dumps(result, indent=2))
