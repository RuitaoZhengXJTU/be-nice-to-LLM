#!/usr/bin/env python3
"""
Image-rec aggregate scorer: 15 problems (clf x5, cnt x5, spt x5) x polite/strict.
Single-seed baseline (n=5/subtype): origin/pv-01-Ryan@4a4cc9e, files <id>_<style>_output.json.
Multi-seed expansion (3 seeds: baseline, 17, 42): adds seed17/42 outputs from 347ab63,
  files <id>_<style>_seed<N>_output.json.  Total 90 cells (15 x 2 x 3).
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
RYAN_COMMIT = "4a4cc9e"
RYAN_COMMIT_MULTISEED = "347ab63"
MODEL = "gpt-4o-mini"
OUTPUT_DIR = "evals/imagerec/outputs"
# Seeds for multi-seed analysis. "baseline" = original single-seed files (no suffix).
SEEDS = ["baseline", 17, 42]

# Ground truth and subtype per problem (from YAML files on pv-01-Ryan)
PROBLEMS = [
    {"id": "clf_01", "subtype": "clf", "ground_truth": {"label": "bear"}},
    {"id": "clf_02", "subtype": "clf", "ground_truth": {"label": "train"}},
    {"id": "clf_03", "subtype": "clf", "ground_truth": {"label": "bus"}},
    {"id": "clf_04", "subtype": "clf", "ground_truth": {"label": "airplane"}},
    {"id": "clf_05", "subtype": "clf", "ground_truth": {"label": "horse"}},
    {"id": "cnt_01", "subtype": "cnt", "ground_truth": {"count": 1}},
    {"id": "cnt_02", "subtype": "cnt", "ground_truth": {"count": 3}},
    {"id": "cnt_03", "subtype": "cnt", "ground_truth": {"count": 2}},
    {"id": "cnt_04", "subtype": "cnt", "ground_truth": {"count": 2}},
    {"id": "cnt_05", "subtype": "cnt", "ground_truth": {"count": 2}},
    {"id": "spt_01", "subtype": "spt", "ground_truth": {"relation": "above"}},
    {"id": "spt_02", "subtype": "spt", "ground_truth": {"relation": "left of"}},
    {"id": "spt_03", "subtype": "spt", "ground_truth": {"relation": "above"}},
    {"id": "spt_04", "subtype": "spt", "ground_truth": {"relation": "right of"}},
    {"id": "spt_05", "subtype": "spt", "ground_truth": {"relation": "below"}},
]


def strip_fence(text: str) -> str:
    """Strip a leading ```<lang>? and trailing ``` from a markdown code fence."""
    s = text.strip()
    s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
    s = re.sub(r"\n?```\s*$", "", s)
    return s.strip()


def load_output(problem_id: str, style: str, seed=None):
    """Load output JSON from Ryan's branch via git show. Returns (outer_data, error).
    seed=None or seed="baseline" -> single-seed filename (no suffix).
    seed=int (17 or 42) -> seeded filename with _seed{N}_ infix.
    """
    if seed is None or seed == "baseline":
        path = f"{OUTPUT_DIR}/{problem_id}_{style}_output.json"
    else:
        path = f"{OUTPUT_DIR}/{problem_id}_{style}_seed{seed}_output.json"
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


def score_output(problem, style, seed=None):
    """
    Score a single output. Returns a result dict with:
    valid_format, accuracy (float or dict for cnt), error (str or None).
    seed=None uses single-seed baseline file.
    """
    pid = problem["id"]
    subtype = problem["subtype"]
    gt = problem["ground_truth"]

    outer, load_err = load_output(pid, style, seed)
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

        # Identical-answer check: compare polite vs strict parsed outputs
        p_parsed = rec["polite"].get("parsed") if rec["polite"] else None
        s_parsed = rec["strict"].get("parsed") if rec["strict"] else None
        if p_parsed is not None and s_parsed is not None:
            rec["polite_strict_identical"] = (p_parsed == s_parsed)
        elif p_parsed is None and s_parsed is None:
            rec["polite_strict_identical"] = None  # both invalid, can't compare
        else:
            rec["polite_strict_identical"] = False  # one valid, one not

        per_problem.append(rec)

    # Build identical-answer summary
    identical_summary = []
    for rec in per_problem:
        flag = rec.get("polite_strict_identical")
        p_parsed = rec["polite"].get("parsed") if rec["polite"] else None
        s_parsed = rec["strict"].get("parsed") if rec["strict"] else None
        identical_summary.append({
            "problem_id": rec["problem_id"],
            "subtype": rec["subtype"],
            "polite_answer": p_parsed,
            "strict_answer": s_parsed,
            "identical": flag,
        })

    n_identical = sum(1 for x in identical_summary if x["identical"] is True)
    n_comparable = sum(1 for x in identical_summary if x["identical"] is not None)

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
        "identical_answer_summary": {
            "n_problems_compared": n_comparable,
            "n_identical": n_identical,
            "all_identical": (n_identical == n_comparable and n_comparable > 0),
            "detail": identical_summary,
        },
        "data_issues": data_issues,
    }


def run_multiseed():
    """
    Score all 90 cells (15 problems x 2 styles x 3 seeds) and compute:
      (a) Per-style accuracy by sub-type pooled over 3 seeds, bootstrap CIs.
      (b) Per-style across-seed answer-stability (for each (problem, style), are all 3 seeds identical?).
      (c) Cross-seed polite=strict identical-answer rate (out of 45 (problem, seed) pairs).
    Returns a structured dict to be merged into the top-level report JSON.
    """
    # cells[(pid, style, seed)] = score_output result dict (valid_format, parsed, accuracy, ...)
    cells = {}
    for prob in PROBLEMS:
        pid = prob["id"]
        for style in ["polite", "strict"]:
            for seed in SEEDS:
                cells[(pid, style, seed)] = score_output(prob, style, seed)

    # ---- (a) Pooled accuracy by (style, subtype) ----
    pooled = {
        "polite": {"clf": [], "cnt_exact": [], "cnt_within_one": [], "spt": [], "if_flags": []},
        "strict": {"clf": [], "cnt_exact": [], "cnt_within_one": [], "spt": [], "if_flags": []},
    }
    for prob in PROBLEMS:
        pid = prob["id"]
        subtype = prob["subtype"]
        for style in ["polite", "strict"]:
            for seed in SEEDS:
                r = cells[(pid, style, seed)]
                if not r["valid_format"]:
                    pooled[style]["if_flags"].append(0)
                else:
                    pooled[style]["if_flags"].append(1)
                    acc = r["accuracy"]
                    if subtype == "clf":
                        pooled[style]["clf"].append(float(acc))
                    elif subtype == "cnt":
                        pooled[style]["cnt_exact"].append(float(acc["exact"]))
                        pooled[style]["cnt_within_one"].append(1.0 if acc["within_one"] else 0.0)
                    elif subtype == "spt":
                        pooled[style]["spt"].append(float(acc))

    def build_pooled_agg(style_key):
        r = pooled[style_key]
        n_cells = len(r["if_flags"])
        n_valid = sum(r["if_flags"])
        return {
            "n_cells_total": n_cells,
            "n_cells_valid": n_valid,
            "instruction_following_rate": round(n_valid / n_cells, 6) if n_cells > 0 else 0.0,
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

    # ---- (b) Per-style across-seed answer stability ----
    def compute_stability(style):
        stable_count = 0
        unstable = []
        for prob in PROBLEMS:
            pid = prob["id"]
            seed_answers = [cells[(pid, style, s)].get("parsed") for s in SEEDS]
            # Stable = all 3 non-None AND all equal (using JSON-serialised comparison)
            if (
                all(a is not None for a in seed_answers)
                and len({json.dumps(a, sort_keys=True) for a in seed_answers}) == 1
            ):
                stable_count += 1
            else:
                entry = {
                    "problem_id": pid,
                    "subtype": prob["subtype"],
                    "answers": {},
                }
                for i, s in enumerate(SEEDS):
                    r = cells[(pid, style, s)]
                    entry["answers"][str(s)] = (
                        seed_answers[i] if r["valid_format"] else "FORMAT_FAILURE"
                    )
                unstable.append(entry)
        return {
            "stable_count": stable_count,
            "n_problems": len(PROBLEMS),
            "unstable_problems": unstable,
        }

    # ---- (c) Cross-seed polite=strict identical-answer rate ----
    n_identical = 0
    non_identical = []
    for prob in PROBLEMS:
        pid = prob["id"]
        problem_identical_count = 0
        per_seed_detail = {}
        for seed in SEEDS:
            p_r = cells[(pid, "polite", seed)]
            s_r = cells[(pid, "strict", seed)]
            p_ans = p_r.get("parsed") if p_r["valid_format"] else None
            s_ans = s_r.get("parsed") if s_r["valid_format"] else None
            is_ident = (p_ans is not None and s_ans is not None and p_ans == s_ans)
            if is_ident:
                n_identical += 1
                problem_identical_count += 1
            per_seed_detail[str(seed)] = {
                "polite": p_ans if p_r["valid_format"] else "FORMAT_FAILURE",
                "strict": s_ans if s_r["valid_format"] else "FORMAT_FAILURE",
                "identical": is_ident,
            }
        if problem_identical_count < len(SEEDS):
            non_identical.append({
                "problem_id": pid,
                "subtype": prob["subtype"],
                "identical_count": problem_identical_count,
                "n_seeds": len(SEEDS),
                "per_seed": per_seed_detail,
            })

    n_pairs_total = len(PROBLEMS) * len(SEEDS)  # 45

    return {
        "meta": {
            "n_problems": len(PROBLEMS),
            "seeds": [str(s) for s in SEEDS],
            "n_seeds": len(SEEDS),
            "n_cells_total": len(PROBLEMS) * 2 * len(SEEDS),
            "source_commit_baseline": RYAN_COMMIT,
            "source_commit_seed_runs": RYAN_COMMIT_MULTISEED,
            "bootstrap_reps": 2000,
            "alpha": 0.05,
        },
        "pooled_accuracy": {
            "polite": build_pooled_agg("polite"),
            "strict": build_pooled_agg("strict"),
        },
        "stability": {
            "polite": compute_stability("polite"),
            "strict": compute_stability("strict"),
        },
        "cross_seed_identical": {
            "n_identical": n_identical,
            "n_pairs_total": n_pairs_total,
            "identical_rate": round(n_identical / n_pairs_total, 6) if n_pairs_total > 0 else 0.0,
            "non_identical_problems": non_identical,
        },
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
        f"All {n*2} outputs are JSON-shaped with finish_reason=stop (per Ryan). "
        f"After fence-stripping and format validation: {pn}/{n} polite and {sn}/{n} strict "
        f"outputs pass check_image_format. "
        f"Valid counts by sub-type: clf polite={pn_clf}, strict={sn_clf}; "
        f"cnt polite={pn_cnt}, strict={sn_cnt}; "
        f"spt polite={pn_spt}, strict={sn_spt}. "
        f"With only 5 problems per sub-type the CIs are still wide -- "
        f"any apparent accuracy gap is likely within noise. "
        f"The signal to watch is the polite/strict identical-answer pattern (see below)."
    )
    lines.append("")

    # Identical-answer analysis section
    ias = report.get("identical_answer_summary", {})
    n_comp = ias.get("n_problems_compared", 0)
    n_ident = ias.get("n_identical", 0)
    all_ident = ias.get("all_identical", False)
    detail = ias.get("detail", [])

    lines.append("## Polite vs Strict Identical-Answer Analysis")
    lines.append("")
    if all_ident:
        lines.append(
            f"Polite and strict returned identical parsed answers on all {n_ident}/{n_comp} "
            f"comparable problems. This pattern holds at n=5 per sub-type."
        )
    else:
        lines.append(
            f"Polite and strict returned identical parsed answers on {n_ident}/{n_comp} "
            f"comparable problems. Divergences:"
        )
    lines.append("")
    diverged = [x for x in detail if x["identical"] is False]
    if diverged:
        lines.append("| Problem | Sub-type | Polite answer | Strict answer |")
        lines.append("|---------|----------|---------------|---------------|")
        for d in diverged:
            pa = str(d["polite_answer"]) if d["polite_answer"] is not None else "INVALID"
            sa = str(d["strict_answer"]) if d["strict_answer"] is not None else "INVALID"
            lines.append(f"| {d['problem_id']} | {d['subtype']} | {pa} | {sa} |")
        lines.append("")
    else:
        lines.append("No divergences -- polite and strict answers are identical on every problem.")
        lines.append("")

    # ---- Multi-seed section ----
    ms = report.get("multiseed")
    if ms:
        ms_meta = ms["meta"]
        pa = ms["pooled_accuracy"]
        stab = ms["stability"]
        csi = ms["cross_seed_identical"]
        seeds_str = ", ".join(ms_meta["seeds"])
        n_cells = ms_meta["n_cells_total"]
        n_seeds = ms_meta["n_seeds"]

        lines.append(
            "## Multi-Seed Analysis "
            f"(seeds: {seeds_str}; "
            f"baseline@{ms_meta['source_commit_baseline']}, "
            f"seed runs@{ms_meta['source_commit_seed_runs']})"
        )
        lines.append("")
        lines.append(
            f"Total cells: {n_cells} ({ms_meta['n_problems']} problems x 2 styles x {n_seeds} seeds). "
            "Single-seed headline numbers above are unchanged; this section extends the picture."
        )
        lines.append("")

        lines.append("### (a) Pooled Accuracy by Sub-type")
        lines.append("")
        lines.append(
            "n = 5 problems x 3 seeds = 15 per (style, sub-type). "
            "Bootstrap CI over 15 accuracy values (or fewer if format failures)."
        )
        lines.append("")

        def ms_ci_str(d):
            if d["mean"] is None:
                return "n/a (0 valid)"
            return f"{d['mean']:.4f} [95% CI: {d['ci_low']:.4f}, {d['ci_high']:.4f}] n={d['n']}"

        ppa = pa["polite"]
        spa = pa["strict"]
        lines.append("| Metric | Polite | Strict |")
        lines.append("|--------|--------|--------|")
        lines.append(
            f"| IF rate ({n_cells//2} cells/style) | "
            f"{ppa['instruction_following_rate']:.3f} ({ppa['n_cells_valid']}/{n_cells//2}) | "
            f"{spa['instruction_following_rate']:.3f} ({spa['n_cells_valid']}/{n_cells//2}) |"
        )
        lines.append(
            f"| clf top-1 accuracy (pooled) | "
            f"{ms_ci_str(ppa['by_subtype']['clf']['top1_accuracy_ci'])} | "
            f"{ms_ci_str(spa['by_subtype']['clf']['top1_accuracy_ci'])} |"
        )
        lines.append(
            f"| cnt exact accuracy (pooled) | "
            f"{ms_ci_str(ppa['by_subtype']['cnt']['exact_accuracy_ci'])} | "
            f"{ms_ci_str(spa['by_subtype']['cnt']['exact_accuracy_ci'])} |"
        )
        lines.append(
            f"| cnt within-one rate (pooled) | "
            f"{ms_ci_str(ppa['by_subtype']['cnt']['within_one_rate_ci'])} | "
            f"{ms_ci_str(spa['by_subtype']['cnt']['within_one_rate_ci'])} |"
        )
        lines.append(
            f"| spt token-exact accuracy (pooled) | "
            f"{ms_ci_str(ppa['by_subtype']['spt']['token_exact_accuracy_ci'])} | "
            f"{ms_ci_str(spa['by_subtype']['spt']['token_exact_accuracy_ci'])} |"
        )
        lines.append("")

        lines.append("### (b) Across-Seed Answer Stability")
        lines.append("")
        stab_p = stab["polite"]
        stab_s = stab["strict"]
        lines.append(
            f"For each (problem, style), do all 3 seeds return the same parsed answer? "
            f"Polite: {stab_p['stable_count']}/{stab_p['n_problems']} stable. "
            f"Strict: {stab_s['stable_count']}/{stab_s['n_problems']} stable."
        )
        lines.append("")
        for style_label, stab_r in [("Polite", stab_p), ("Strict", stab_s)]:
            if stab_r["unstable_problems"]:
                lines.append(f"**{style_label} unstable problems:**")
                lines.append("")
                lines.append("| Problem | Sub-type | baseline | seed17 | seed42 |")
                lines.append("|---------|----------|----------|--------|--------|")
                for u in stab_r["unstable_problems"]:
                    a = u["answers"]
                    lines.append(
                        f"| {u['problem_id']} | {u['subtype']} | "
                        f"{a.get('baseline', '?')} | {a.get('17', '?')} | {a.get('42', '?')} |"
                    )
                lines.append("")
        if stab_p["stable_count"] == stab_p["n_problems"] and stab_s["stable_count"] == stab_s["n_problems"]:
            lines.append(
                "All 15 problems are seed-stable for both styles -- "
                "the model's parsed answer does not vary across seeds."
            )
            lines.append("")

        lines.append("### (c) Cross-Seed Polite=Strict Identical-Answer Rate")
        lines.append("")
        n_ident = csi["n_identical"]
        n_pairs = csi["n_pairs_total"]
        rate = csi["identical_rate"]
        lines.append(
            f"Out of {n_pairs} (problem, seed) pairs, polite and strict returned the same "
            f"parsed answer on {n_ident} ({rate:.3f})."
        )
        lines.append("")
        non_ident = csi["non_identical_problems"]
        if non_ident:
            lines.append("Per-problem breakdown for problems with < 3/3 identical seeds:")
            lines.append("")
            for ni in non_ident:
                lines.append(
                    f"**{ni['problem_id']}** ({ni['subtype']}): "
                    f"{ni['identical_count']}/{ni['n_seeds']} seeds identical"
                )
                for seed_k, sd in ni["per_seed"].items():
                    marker = "=" if sd["identical"] else "!="
                    lines.append(
                        f"  - seed={seed_k}: polite={sd['polite']}  {marker}  strict={sd['strict']}"
                    )
                lines.append("")
        else:
            lines.append(
                f"All {n_pairs} pairs are identical -- "
                "polite and strict give the same answer on every (problem, seed) combination."
            )
            lines.append("")

    # ---- Data Issues ----
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
        lines.append(f"None -- all {n*2} outputs parsed and passed check_image_format.")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    report = run()

    print("Running multi-seed analysis (90 cells)...")
    ms_report = run_multiseed()
    report["multiseed"] = ms_report

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
    n = report["meta"]["n_problems"]
    print(f"\n--- Single-seed headline (n=5/subtype) ---")
    print(f"Polite: IF={p['instruction_following_rate_raw']:.3f} ({p['n_valid_format']}/{n})")
    print(f"Strict: IF={s['instruction_following_rate_raw']:.3f} ({s['n_valid_format']}/{n})")
    ias = report["identical_answer_summary"]
    print(f"Identical answers: {ias['n_identical']}/{ias['n_problems_compared']} "
          f"(all_identical={ias['all_identical']})")
    print(f"Data issues: {len(report['data_issues'])}")

    print(f"\n--- Multi-seed pooled (3 seeds, 90 cells) ---")
    ms_pa = ms_report["pooled_accuracy"]
    ms_csi = ms_report["cross_seed_identical"]
    ms_stab = ms_report["stability"]
    for style in ["polite", "strict"]:
        pa_s = ms_pa[style]
        clf_ci = pa_s["by_subtype"]["clf"]["top1_accuracy_ci"]
        cnt_ci = pa_s["by_subtype"]["cnt"]["exact_accuracy_ci"]
        spt_ci = pa_s["by_subtype"]["spt"]["token_exact_accuracy_ci"]
        print(f"{style.capitalize()}: clf={clf_ci['mean']:.3f} cnt_exact={cnt_ci['mean']:.3f} "
              f"spt={spt_ci['mean']:.3f}")
    print(f"Cross-seed polite=strict: {ms_csi['n_identical']}/{ms_csi['n_pairs_total']} "
          f"({ms_csi['identical_rate']:.3f})")
    print(f"Stability: polite={ms_stab['polite']['stable_count']}/{ms_stab['polite']['n_problems']}, "
          f"strict={ms_stab['strict']['stable_count']}/{ms_stab['strict']['n_problems']}")
