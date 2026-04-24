#!/usr/bin/env python3
"""
Image-rec aggregate scorer: 9 problems (clf x3, cnt x3, spt x3) x polite/strict.
Reads outputs from origin/pv-01-Ryan (commit fae616f) via git show.
Strips markdown code fences from raw_text before JSON parsing.
Uses grade_image.py for format checks and accuracy computation.
Bootstrap CI config: 2000 reps, alpha=0.05, percentile method (same as run_aggregate.py).
Outputs: evals/imagerec/aggregate_report.json
         evals/imagerec/AGGREGATE_SUMMARY.md
"""
import json
import random
import re
import subprocess
import sys
from pathlib import Path

# Make grade_image importable from the project root
sys.path.insert(0, str(Path(__file__).parent / "evals" / "imagerec"))
from grade_image import check_image_format, image_accuracy, CountResult  # noqa: E402

RYAN_BRANCH = "origin/pv-01-Ryan"
RYAN_COMMIT = "fae616f"
MODEL = "gpt-4o-mini"
OUTPUT_DIR = "evals/imagerec/outputs"

# Ground truth and subtype per problem (from YAML files on pv-01-Ryan)
PROBLEMS = [
    {"id": "clf_01", "subtype": "clf", "ground_truth": {"label": "bear"}},
    {"id": "clf_02", "subtype": "clf", "ground_truth": {"label": "train"}},
    {"id": "clf_03", "subtype": "clf", "ground_truth": {"label": "bus"}},
    {"id": "cnt_01", "subtype": "cnt", "ground_truth": {"count": 1}},
    {"id": "cnt_02", "subtype": "cnt", "ground_truth": {"count": 3}},
    {"id": "cnt_03", "subtype": "cnt", "ground_truth": {"count": 2}},
    {"id": "spt_01", "subtype": "spt", "ground_truth": {"relation": "above"}},
    {"id": "spt_02", "subtype": "spt", "ground_truth": {"relation": "left of"}},
    {"id": "spt_03", "subtype": "spt", "ground_truth": {"relation": "above"}},
]


def strip_fence(text: str) -> str:
    """Strip a leading ```<lang>? and trailing ``` from a markdown code fence."""
    s = text.strip()
    s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
    s = re.sub(r"\n?```\s*$", "", s)
    return s.strip()


def load_output(problem_id: str, style: str):
    """Load output JSON from Ryan's branch via git show. Returns (outer_data, error)."""
    path = f"{OUTPUT_DIR}/{problem_id}_{style}_output.json"
    r = subprocess.run(
        ["git", "show", f"{RYAN_BRANCH}:{path}"],
        capture_output=True, text=True,
    )
    raw = r.stdout.strip()
    if not raw:
        return None, f"git show returned empty output for {path}"
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as e:
        return None, f"outer JSONDecodeError: {e}"


def parse_inner(raw_text: str):
    """
    Strip fence and parse inner JSON. Returns (parsed_dict, error_or_None).
    On any failure returns (None, error_message).
    """
    if not isinstance(raw_text, str):
        return None, "raw_text is not a string"
    stripped = strip_fence(raw_text)
    try:
        return json.loads(stripped), None
    except json.JSONDecodeError as e:
        return None, f"inner JSONDecodeError after fence-strip: {e}"


def bootstrap_ci(values, n_boot=2000, alpha=0.05, seed=42):
    """Non-parametric bootstrap CI for mean. Same config as run_aggregate.py."""
    rng = random.Random(seed)
    n = len(values)
    if n == 0:
        return {"mean": None, "ci_low": None, "ci_high": None, "n": 0}
    if n == 1:
        return {"mean": values[0], "ci_low": values[0], "ci_high": values[0], "n": 1}
    boot_means = []
    for _ in range(n_boot):
        s = [rng.choice(values) for _ in range(n)]
        boot_means.append(sum(s) / n)
    boot_means.sort()
    lo = int((alpha / 2) * n_boot)
    hi = int((1 - alpha / 2) * n_boot) - 1
    return {
        "mean": sum(values) / n,
        "ci_low": boot_means[lo],
        "ci_high": boot_means[hi],
        "n": n,
    }


def score_output(problem, style):
    """
    Score a single output. Returns a result dict with:
    valid_format, accuracy (float or dict for cnt), error (str or None).
    """
    pid = problem["id"]
    subtype = problem["subtype"]
    gt = problem["ground_truth"]

    outer, load_err = load_output(pid, style)
    if outer is None:
        return {"valid_format": False, "error": load_err, "raw_text": None,
                "parsed": None, "accuracy": None}

    raw_text = outer.get("raw_text", "")
    parsed, parse_err = parse_inner(raw_text)

    if parsed is None:
        return {"valid_format": False, "error": parse_err, "raw_text": raw_text,
                "parsed": None, "accuracy": None}

    # Build a spec dict for check_image_format
    if subtype == "clf":
        spec = {"sub_type": "clf"}
        gt_val = gt["label"]
    elif subtype == "cnt":
        spec = {"sub_type": "cnt"}
        gt_val = gt["count"]
    else:  # spt
        spec = {"sub_type": "spt"}
        gt_val = gt["relation"]

    valid = check_image_format(parsed, spec)
    if not valid:
        return {"valid_format": False, "error": "check_image_format returned False",
                "raw_text": raw_text, "parsed": parsed, "accuracy": None}

    acc = image_accuracy(parsed, gt_val, subtype)

    if isinstance(acc, CountResult):
        acc_serializable = {"exact": acc.exact, "within_one": acc.within_one}
    else:
        acc_serializable = acc

    return {
        "valid_format": True,
        "error": None,
        "raw_text": raw_text,
        "parsed": parsed,
        "accuracy": acc_serializable,
    }


def run():
    per_problem = []
    data_issues = []

    # Collect per-style, per-subtype accuracy lists
    # Each entry: (subtype, style, accuracy_value)
    results = {
        "polite": {"clf": [], "cnt_exact": [], "cnt_within_one": [], "spt": [], "if_flags": []},
        "strict": {"clf": [], "cnt_exact": [], "cnt_within_one": [], "spt": [], "if_flags": []},
    }

    for prob in PROBLEMS:
        pid = prob["id"]
        subtype = prob["subtype"]
        rec = {"problem_id": pid, "subtype": subtype,
               "ground_truth": prob["ground_truth"],
               "polite": None, "strict": None}

        for style in ["polite", "strict"]:
            result = score_output(prob, style)
            rec[style] = result

            if not result["valid_format"]:
                issue = f"{pid}_{style}: format invalid -- {result['error']}"
                data_issues.append(issue)
                results[style]["if_flags"].append(0)
            else:
                results[style]["if_flags"].append(1)
                acc = result["accuracy"]
                if subtype == "clf":
                    results[style]["clf"].append(acc)
                elif subtype == "cnt":
                    results[style]["cnt_exact"].append(acc["exact"])
                    results[style]["cnt_within_one"].append(1.0 if acc["within_one"] else 0.0)
                elif subtype == "spt":
                    results[style]["spt"].append(acc)

        per_problem.append(rec)

    n_total = len(PROBLEMS)

    def build_style_agg(style_key):
        r = results[style_key]
        n_valid = sum(r["if_flags"])
        return {
            "n_outputs": n_total,
            "n_valid_format": n_valid,
            "instruction_following_rate_raw": round(n_valid / n_total, 6),
            "instruction_following_rate_ci": bootstrap_ci(r["if_flags"]),
            "by_subtype": {
                "clf": {
                    "n_valid": len(r["clf"]),
                    "top1_accuracy_ci": bootstrap_ci(r["clf"]),
                },
                "cnt": {
                    "n_valid": len(r["cnt_exact"]),
                    "exact_accuracy_ci": bootstrap_ci(r["cnt_exact"]),
                    "within_one_rate_ci": bootstrap_ci(r["cnt_within_one"]),
                },
                "spt": {
                    "n_valid": len(r["spt"]),
                    "token_exact_accuracy_ci": bootstrap_ci(r["spt"]),
                },
            },
        }

    agg = {
        "polite": build_style_agg("polite"),
        "strict": build_style_agg("strict"),
    }

    return {
        "meta": {
            "model": MODEL,
            "source_branch": "pv-01-Ryan",
            "source_commit": RYAN_COMMIT,
            "n_problems": n_total,
            "n_outputs": n_total * 2,
            "bootstrap_reps": 2000,
            "alpha": 0.05,
            "ci_method": "percentile",
        },
        "aggregate": agg,
        "per_problem": per_problem,
        "data_issues": data_issues,
    }


def generate_summary(report):
    meta = report["meta"]
    agg = report["aggregate"]
    per = report["per_problem"]
    issues = report["data_issues"]
    p = agg["polite"]
    s = agg["strict"]

    def ci_str(d):
        if d["mean"] is None:
            return "n/a (0 valid)"
        return f"{d['mean']:.4f} [95% CI: {d['ci_low']:.4f}, {d['ci_high']:.4f}] n={d['n']}"

    lines = []
    lines.append("# imagerec Aggregate Evaluation Report")
    lines.append("")
    lines.append(
        f"Model: {meta['model']}  |  Source: pv-01-Ryan @ {meta['source_commit']}  |  "
        f"Graded on: pv-01-Jeremy"
    )
    lines.append(f"Bootstrap: {meta['bootstrap_reps']} reps, alpha={meta['alpha']}, percentile method")
    lines.append("")
    lines.append("## Headline Numbers")
    lines.append("")
    lines.append(
        f"Instruction-following rate = fraction of {meta['n_problems']} problems with valid JSON + "
        f"required key + correct type."
    )
    lines.append(
        "Accuracy per sub-type is computed only over valid-format outputs "
        "(clf: top-1 exact case-insensitive; cnt: exact integer match primary + within-one secondary; "
        "spt: token-exact against ALLOWED_RELATIONS)."
    )
    lines.append("")
    lines.append("| Metric | Polite | Strict |")
    lines.append("|--------|--------|--------|")

    n = meta["n_problems"]
    lines.append(
        f"| IF rate (n={n}) | "
        f"{p['instruction_following_rate_raw']:.3f} ({p['n_valid_format']}/{n}) | "
        f"{s['instruction_following_rate_raw']:.3f} ({s['n_valid_format']}/{n}) |"
    )
    p_if_ci = p["instruction_following_rate_ci"]
    s_if_ci = s["instruction_following_rate_ci"]
    lines.append(
        f"| IF rate 95% CI | [{p_if_ci['ci_low']:.3f}, {p_if_ci['ci_high']:.3f}] | "
        f"[{s_if_ci['ci_low']:.3f}, {s_if_ci['ci_high']:.3f}] |"
    )
    p_clf = p["by_subtype"]["clf"]["top1_accuracy_ci"]
    s_clf = s["by_subtype"]["clf"]["top1_accuracy_ci"]
    lines.append(
        f"| clf top-1 accuracy | {ci_str(p_clf)} | {ci_str(s_clf)} |"
    )
    p_cnt_e = p["by_subtype"]["cnt"]["exact_accuracy_ci"]
    s_cnt_e = s["by_subtype"]["cnt"]["exact_accuracy_ci"]
    lines.append(
        f"| cnt exact accuracy | {ci_str(p_cnt_e)} | {ci_str(s_cnt_e)} |"
    )
    p_cnt_w = p["by_subtype"]["cnt"]["within_one_rate_ci"]
    s_cnt_w = s["by_subtype"]["cnt"]["within_one_rate_ci"]
    lines.append(
        f"| cnt within-one rate | {ci_str(p_cnt_w)} | {ci_str(s_cnt_w)} |"
    )
    p_spt = p["by_subtype"]["spt"]["token_exact_accuracy_ci"]
    s_spt = s["by_subtype"]["spt"]["token_exact_accuracy_ci"]
    lines.append(
        f"| spt token-exact accuracy | {ci_str(p_spt)} | {ci_str(s_spt)} |"
    )
    lines.append("")

    lines.append("## Per-Problem Results")
    lines.append("")
    lines.append("| ID | Sub-type | GT | Polite valid | Polite acc | Strict valid | Strict acc |")
    lines.append("|----|----------|----|--------------|------------|--------------|------------|")

    for rec in per:
        pid = rec["problem_id"]
        st = rec["subtype"]
        gt = rec["ground_truth"]
        gt_str = "/".join(f"{k}={v}" for k, v in gt.items())

        def fmt_rec(r):
            if r is None:
                return "N/A", "-"
            if not r.get("valid_format"):
                err = r.get("error", "?")
                short = err[:30] + "..." if len(err) > 30 else err
                return f"FAIL: {short}", "-"
            acc = r.get("accuracy")
            if isinstance(acc, dict) and "exact" in acc:
                return "VALID", f"exact={acc['exact']:.1f} w1={acc['within_one']}"
            return "VALID", f"{acc:.3f}"

        pv, pa = fmt_rec(rec["polite"])
        sv, sa = fmt_rec(rec["strict"])
        lines.append(f"| {pid} | {st} | {gt_str} | {pv} | {pa} | {sv} | {sa} |")

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")

    pn = p["n_valid_format"]
    sn = s["n_valid_format"]
    pn_clf = p["by_subtype"]["clf"]["n_valid"]
    sn_clf = s["by_subtype"]["clf"]["n_valid"]
    pn_cnt = p["by_subtype"]["cnt"]["n_valid"]
    sn_cnt = s["by_subtype"]["cnt"]["n_valid"]
    pn_spt = p["by_subtype"]["spt"]["n_valid"]
    sn_spt = s["by_subtype"]["spt"]["n_valid"]

    lines.append(
        f"All 18 outputs are JSON-shaped with finish_reason=stop (per Ryan). "
        f"After fence-stripping and format validation: {pn}/{n} polite and {sn}/{n} strict "
        f"outputs pass check_image_format. "
        f"Valid counts by sub-type: clf polite={pn_clf}, strict={sn_clf}; "
        f"cnt polite={pn_cnt}, strict={sn_cnt}; "
        f"spt polite={pn_spt}, strict={sn_spt}. "
        f"With only 3 problems per sub-type the CIs are very wide -- "
        f"any style gap visible here is within noise. "
        f"More problems per sub-type are needed before drawing conclusions about polite vs strict accuracy."
    )
    lines.append("")

    if issues:
        lines.append("## Data Issues")
        lines.append("")
        lines.append(
            f"{len(issues)} output(s) failed format validation and are excluded from accuracy CIs:"
        )
        lines.append("")
        for issue in issues:
            lines.append(f"- {issue}")
        lines.append("")
    else:
        lines.append("## Data Issues")
        lines.append("")
        lines.append("None -- all 18 outputs parsed and passed check_image_format.")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    report = run()

    out_dir = Path("evals/imagerec")
    out_dir.mkdir(parents=True, exist_ok=True)

    rp = out_dir / "aggregate_report.json"
    with open(rp, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Wrote {rp}")

    sp = out_dir / "AGGREGATE_SUMMARY.md"
    with open(sp, "w") as f:
        f.write(generate_summary(report))
    print(f"Wrote {sp}")

    agg = report["aggregate"]
    p = agg["polite"]
    s = agg["strict"]
    print(f"\nPolite: IF={p['instruction_following_rate_raw']:.3f} ({p['n_valid_format']}/9)")
    print(f"  clf={ci_str(p['by_subtype']['clf']['top1_accuracy_ci'])}" if False else "")
    print(f"Strict: IF={s['instruction_following_rate_raw']:.3f} ({s['n_valid_format']}/9)")
    print(f"Data issues: {len(report['data_issues'])}")
