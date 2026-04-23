#!/usr/bin/env python3
"""
Compare agent outputs (polite vs strict) against Pyomo baseline.

Single-instance usage:
  python compare_results.py baseline.json polite.json strict.json

Multi-instance usage (bootstrap CI across instances):
  python compare_results.py --multi \
    --baseline b1.json b2.json b3.json \
    --polite   p1.json p2.json p3.json \
    --strict   s1.json s2.json s3.json
"""
import argparse
import json
import random
import sys
from typing import Optional


def load_json(path: str) -> Optional[dict]:
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"  Load error: {e}")
        return None


def check_format(data: dict, n: int = 100) -> tuple:
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
    polite_path: Optional[str] = None,
    strict_path: Optional[str] = None,
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


# ---------------------------------------------------------------------------
# Bootstrap CI utilities
# ---------------------------------------------------------------------------

def _bootstrap_ci(
    values: list,
    n_boot: int = 2000,
    alpha: float = 0.05,
    seed: int = 42,
) -> dict:
    """
    Non-parametric bootstrap CI for the mean of `values`.
    Returns {mean, ci_low, ci_high, n} at confidence level 1 - alpha.
    Uses the percentile method.
    """
    rng = random.Random(seed)
    n = len(values)
    if n == 0:
        return {"mean": None, "ci_low": None, "ci_high": None, "n": 0}
    if n == 1:
        return {"mean": values[0], "ci_low": values[0], "ci_high": values[0], "n": 1}

    boot_means = []
    for _ in range(n_boot):
        sample = [rng.choice(values) for _ in range(n)]
        boot_means.append(sum(sample) / n)
    boot_means.sort()

    lo_idx = int((alpha / 2) * n_boot)
    hi_idx = int((1 - alpha / 2) * n_boot) - 1
    return {
        "mean": sum(values) / n,
        "ci_low": boot_means[lo_idx],
        "ci_high": boot_means[hi_idx],
        "n": n,
    }


def compare_multi(
    baseline_paths: list,
    polite_paths: list,
    strict_paths: list,
    n: int = 100,
    n_boot: int = 2000,
    alpha: float = 0.05,
) -> dict:
    """
    Run per-instance comparisons and aggregate with bootstrap CI.
    Reports CI for optimality_gap and instruction_following_rate
    across all instances for each prompt style.
    """
    if not (len(baseline_paths) == len(polite_paths) == len(strict_paths)):
        return {"error": "baseline, polite, and strict lists must have the same length"}

    per_instance = []
    agg = {
        "polite": {"opt_gaps": [], "if_flags": []},
        "strict": {"opt_gaps": [], "if_flags": []},
    }

    for i, (bp, pp, sp) in enumerate(zip(baseline_paths, polite_paths, strict_paths)):
        rec = compare(bp, pp, sp, n=n)
        rec["instance_index"] = i
        per_instance.append(rec)

        for style in ("polite", "strict"):
            sr = rec.get(style)
            if sr and sr.get("valid"):
                agg[style]["opt_gaps"].append(sr["optimality_gap"])
                agg[style]["if_flags"].append(
                    1 if sr.get("instruction_following") == "ok" else 0
                )

    summary = {}
    for style in ("polite", "strict"):
        gaps = agg[style]["opt_gaps"]
        ifs = agg[style]["if_flags"]
        summary[style] = {
            "optimality_gap": _bootstrap_ci(gaps, n_boot=n_boot, alpha=alpha),
            "instruction_following_rate": _bootstrap_ci(ifs, n_boot=n_boot, alpha=alpha),
            "n_valid_instances": len(gaps),
        }

    return {"per_instance": per_instance, "aggregate_bootstrap_ci": summary}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare polite vs strict agent outputs against Pyomo baseline."
    )
    parser.add_argument(
        "--multi",
        action="store_true",
        help="Aggregate across multiple instances with bootstrap CI.",
    )
    parser.add_argument("--baseline", nargs="+", metavar="FILE")
    parser.add_argument("--polite", nargs="+", metavar="FILE")
    parser.add_argument("--strict", nargs="+", metavar="FILE")
    parser.add_argument("--n", type=int, default=100, help="Expected x vector length")
    parser.add_argument("--n-boot", type=int, default=2000, help="Bootstrap replicates")
    parser.add_argument("--alpha", type=float, default=0.05, help="CI alpha level")
    parser.add_argument("args", nargs="*")
    opts = parser.parse_args()

    if opts.multi:
        if not (opts.baseline and opts.polite and opts.strict):
            print("Error: --multi requires --baseline, --polite, and --strict file lists.")
            sys.exit(1)
        result = compare_multi(
            opts.baseline,
            opts.polite,
            opts.strict,
            n=opts.n,
            n_boot=opts.n_boot,
            alpha=opts.alpha,
        )
    else:
        positional = opts.args
        if len(positional) < 1:
            print("Usage (single): python compare_results.py baseline.json [polite.json] [strict.json]")
            print("Usage (multi):  python compare_results.py --multi --baseline b1.json ... --polite p1.json ... --strict s1.json ...")
            sys.exit(1)
        baseline = positional[0]
        polite = positional[1] if len(positional) > 1 else None
        strict = positional[2] if len(positional) > 2 else None
        result = compare(baseline, polite, strict, n=opts.n)

    print(json.dumps(result, indent=2))
