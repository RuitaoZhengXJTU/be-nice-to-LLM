#!/usr/bin/env python3
"""
Aggregate scorer for nlp_100_20: 8 instances (01-06, 08, 09) x polite/strict.
instance_07 pre-excluded: 200-var strict truncates at gpt-4o-mini 16384-token cap.
instance_10 pre-excluded: 150-var strict truncates at gpt-4o-mini 16384-token cap.
Going-forward rule: any instance where either style truncates is excluded.
Reads outputs from origin/pv-01-Ryan (commit b564a85).
Baselines computed analytically (proofs in docstrings below).
Outputs: evals/nlp_100_20/aggregate_report.json
         evals/nlp_100_20/AGGREGATE_SUMMARY.md
"""
import json
import math
import random
import subprocess
from pathlib import Path

RYAN_BRANCH = "origin/pv-01-Ryan"
RYAN_COMMIT = "b564a85"
MODEL = "gpt-4o-mini"

EXCLUDED_INSTANCES = {
    "07": (
        "200-var problem. gpt-4o-mini hard cap is max_tokens=16384; strict output "
        "truncates mid-vector at that cap, polite returns prose. Re-run at max_tokens=16384 "
        "still truncates (pv-01-Ryan@0da7d64). Going-forward rule: any instance where "
        "either style truncates is excluded from aggregate scoring."
    ),
    "10": (
        "150-var problem. gpt-4o-mini hard cap is max_tokens=16384; strict output "
        "truncates at that cap (finish_reason=length), polite returns prose. "
        "Documented in pv-01-Ryan@b564a85. Same going-forward exclusion rule as instance_07."
    ),
}


def compute_baselines():
    """
    Analytic ground-truth solutions for all 7 instances.

    i01: min sum(x^2), sum(x)>=0 (x20), [-10,10]
         Optimal x=0 (unconstrained min satisfies constraint). obj=0.
    i02: min sum(x), sum(x^2)<=1000 (x20), [-5,5]
         KKT: x[i]=c uniform; 100c^2=1000 -> c=sqrt(10); minimize-> c=-sqrt(10). obj=-100*sqrt(10).
    i03: min sum((x-1)^2), sum(x)>=0 (x20), [-10,10]
         Unconstrained min at x=1 gives sum=100>=0. obj=0.
    i04: min sum(x^2,i=1..10), sum(x)>=1; sum(x^2,i=1..5)<=4; sum(x,i=6..10)>=-1
         KKT with only first constraint active: x[i]=0.1 uniform. obj=0.1.
    i05: min sum(x^2,i=1..50), j=1..15: sum(x,group_j)>=j*0.1 (groups of 3), [-10,10]
         Within each group of 3: uniform x=j*0.1/3. x[45..49]=0. obj=sum_j (j*0.1)^2/3.
    i06: min sum(x^2,i=1..100), j=1..30: sum(x,group_j)>=j*0.1 (groups of 3), [-10,10]
         Within each group of 3: uniform x=j*0.1/3. x[90..99]=0. obj=sum_j (j*0.1)^2/3.
    i07: min sum(x^2,i=1..200), j=1..25: sum(x,group_j)>=j*0.2 (groups of 8), [-5,5]
         Within each group of 8: uniform x=j*0.2/8. obj=sum_j 8*(j*0.025)^2.
    i08: min sum(x^2,i=1..50), j=1..10: sum(x,group_j)>=j*0.5 (groups of 5, 5j-4..5j), [-10,10]
         Within each group of 5: uniform x=j*0.5/5=j*0.1. obj=sum_j=1..10 5*(j*0.1)^2=0.05*385=19.25.
    i09: min sum(x^2,i=1..100), j=1..20: sum(x,group_j)>=j*0.5 (groups of 5, 5j-4..5j), [-10,10]
         Within each group of 5: uniform x=j*0.1. obj=sum_j=1..20 5*(j*0.1)^2=0.05*2870=143.5.
    """
    sqrt10 = math.sqrt(10)
    b = {}

    b["01"] = {"n": 100, "x": [0.0]*100, "objective_value": 0.0}

    x2 = -sqrt10
    b["02"] = {"n": 100, "x": [round(x2, 10)]*100,
               "objective_value": round(-100.0 * sqrt10, 10)}

    b["03"] = {"n": 100, "x": [1.0]*100, "objective_value": 0.0}

    b["04"] = {"n": 10, "x": [0.1]*10, "objective_value": 0.1}

    x5 = [0.0]*50
    obj5 = 0.0
    for j in range(1, 16):
        v = j * 0.1 / 3.0
        for k in range(3):
            x5[3*(j-1)+k] = v
        obj5 += 3.0 * v**2
    b["05"] = {"n": 50, "x": [round(v, 10) for v in x5], "objective_value": round(obj5, 10)}

    x6 = [0.0]*100
    obj6 = 0.0
    for j in range(1, 31):
        v = j * 0.1 / 3.0
        for k in range(3):
            x6[3*(j-1)+k] = v
        obj6 += 3.0 * v**2
    b["06"] = {"n": 100, "x": [round(v, 10) for v in x6], "objective_value": round(obj6, 10)}

    x7 = [0.0]*200
    obj7 = 0.0
    for j in range(1, 26):
        v = j * 0.2 / 8.0
        for k in range(8):
            x7[8*(j-1)+k] = v
        obj7 += 8.0 * v**2
    b["07"] = {"n": 200, "x": [round(v, 10) for v in x7], "objective_value": round(obj7, 10)}

    x8 = [0.0]*50
    obj8 = 0.0
    for j in range(1, 11):
        v = j * 0.5 / 5.0
        for k in range(5):
            x8[5*(j-1)+k] = v
        obj8 += 5.0 * v**2
    b["08"] = {"n": 50, "x": [round(v, 10) for v in x8], "objective_value": round(obj8, 10)}

    x9 = [0.0]*100
    obj9 = 0.0
    for j in range(1, 21):
        v = j * 0.5 / 5.0
        for k in range(5):
            x9[5*(j-1)+k] = v
        obj9 += 5.0 * v**2
    b["09"] = {"n": 100, "x": [round(v, 10) for v in x9], "objective_value": round(obj9, 10)}

    return b


def load_from_git(iid, style):
    path = f"evals/nlp_100_20/outputs/instance_{iid}_{style}_output.json"
    r = subprocess.run(["git", "show", f"{RYAN_BRANCH}:{path}"],
                       capture_output=True, text=True)
    raw = r.stdout.strip()
    if not raw:
        return None, "empty git show output"
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as e:
        return None, f"JSONDecodeError: {e}"


def check_format(data, n):
    if not isinstance(data, dict):
        return False, "not a dict"
    if "x" not in data or "objective_value" not in data:
        return False, "missing x or objective_value key"
    if len(data["x"]) != n:
        return False, f"x length {len(data['x'])} != expected {n}"
    if not isinstance(data["objective_value"], (int, float)):
        return False, "objective_value not numeric"
    return True, "ok"


def opt_gap(obj_agent, obj_ref, eps=1e-8):
    return abs(obj_agent - obj_ref) / max(abs(obj_ref), eps)


def bootstrap_ci(values, n_boot=2000, alpha=0.05, seed=42):
    rng = random.Random(seed)
    n = len(values)
    if n == 0:
        return {"mean": None, "ci_low": None, "ci_high": None, "n": 0}
    if n == 1:
        return {"mean": values[0], "ci_low": values[0], "ci_high": values[0], "n": 1}
    boot_means = []
    for _ in range(n_boot):
        s = [rng.choice(values) for _ in range(n)]
        boot_means.append(sum(s)/n)
    boot_means.sort()
    lo = int((alpha/2)*n_boot)
    hi = int((1-alpha/2)*n_boot) - 1
    return {"mean": sum(values)/n,
            "ci_low": boot_means[lo],
            "ci_high": boot_means[hi],
            "n": n}


def run():
    baselines = compute_baselines()
    per_instance = []
    data_issues = []

    polite_if = []   # 1 or 0, over all 8 instances (01-06, 08, 09)
    strict_if = []
    polite_gaps = []  # only for valid-format instances
    strict_gaps = []

    for iid in ["01", "02", "03", "04", "05", "06", "08", "09"]:
        b = baselines[iid]
        n, obj_ref = b["n"], b["objective_value"]
        rec = {"instance_id": iid, "n_vars": n, "baseline_objective": obj_ref,
               "polite": None, "strict": None}

        for style in ["polite", "strict"]:
            data, load_err = load_from_git(iid, style)
            if data is None:
                issue = f"instance_{iid}_{style}: load failed -- {load_err}"
                data_issues.append(issue)
                rec[style] = {"valid": False, "error": load_err,
                              "instruction_following": 0}
                (polite_if if style == "polite" else strict_if).append(0)
                continue

            ok, fmt_err = check_format(data, n)
            if not ok:
                issue = f"instance_{iid}_{style}: format check failed -- {fmt_err}"
                data_issues.append(issue)
                rec[style] = {"valid": False, "error": fmt_err,
                              "instruction_following": 0,
                              "objective_value_reported": data.get("objective_value")}
                (polite_if if style == "polite" else strict_if).append(0)
                continue

            obj = data["objective_value"]
            gap = opt_gap(obj, obj_ref)
            rec[style] = {"valid": True, "objective_value": obj,
                          "optimality_gap": gap, "instruction_following": 1}
            if style == "polite":
                polite_if.append(1)
                polite_gaps.append(gap)
            else:
                strict_if.append(1)
                strict_gaps.append(gap)

        per_instance.append(rec)

    agg = {
        "polite": {
            "n_instances_total": 8,
            "n_instances_valid_format": sum(polite_if),
            "instruction_following_rate_raw": round(sum(polite_if)/8, 6),
            "instruction_following_rate_ci_all8": bootstrap_ci(polite_if),
            "optimality_gap_valid_only": bootstrap_ci(polite_gaps),
            "note_gap_ci": "CI computed over valid-format instances only; n is very small, interpret with caution",
        },
        "strict": {
            "n_instances_total": 8,
            "n_instances_valid_format": sum(strict_if),
            "instruction_following_rate_raw": round(sum(strict_if)/8, 6),
            "instruction_following_rate_ci_all8": bootstrap_ci(strict_if),
            "optimality_gap_valid_only": bootstrap_ci(strict_gaps),
            "note_gap_ci": "CI computed over valid-format instances only; n is very small, interpret with caution",
        },
    }

    return {
        "meta": {"model": MODEL, "source_branch": "pv-01-Ryan",
                 "source_commit": RYAN_COMMIT, "n_instances": 8,
                 "n_instances_excluded": 2,
                 "excluded_instances": EXCLUDED_INSTANCES,
                 "bootstrap_reps": 2000, "alpha": 0.05,
                 "ci_method": "percentile"},
        "aggregate": agg,
        "per_instance": per_instance,
        "data_issues": data_issues,
    }


def generate_summary(report):
    agg = report["aggregate"]
    meta = report["meta"]
    per = report["per_instance"]
    issues = report["data_issues"]
    p = agg["polite"]
    s = agg["strict"]

    def ci_str(d):
        if d["mean"] is None:
            return "n/a (0 valid)"
        return f"{d['mean']:.4f} [95% CI: {d['ci_low']:.4f}, {d['ci_high']:.4f}] n={d['n']}"

    lines = []
    lines.append("# NLP_100_20 Aggregate Evaluation Report")
    lines.append("")
    lines.append(f"Model: {meta['model']}  |  Source: pv-01-Ryan @ {meta['source_commit']}  |  Graded on: pv-01-Jeremy")
    lines.append(f"Bootstrap: {meta['bootstrap_reps']} reps, alpha={meta['alpha']}, percentile method")
    lines.append("")
    lines.append("## Headline Numbers")
    lines.append("")
    lines.append("Instruction-following rate = fraction of 8 instances (01-06, 08, 09) with valid JSON + correct x-vector length + numeric objective.")
    lines.append("instance_07 and instance_10 are pre-excluded (see Data Issues below). Optimality gap = |obj_agent - obj_baseline| / |obj_baseline| (computed only over valid-format outputs).")
    lines.append("")
    lines.append("| Metric | Polite | Strict |")
    lines.append("|--------|--------|--------|")
    lines.append(f"| IF rate (n=8) | {p['instruction_following_rate_raw']:.3f} ({p['n_instances_valid_format']}/8) | {s['instruction_following_rate_raw']:.3f} ({s['n_instances_valid_format']}/8) |")

    p_if_ci = p["instruction_following_rate_ci_all8"]
    s_if_ci = s["instruction_following_rate_ci_all8"]
    lines.append(f"| IF rate 95% CI | [{p_if_ci['ci_low']:.3f}, {p_if_ci['ci_high']:.3f}] | [{s_if_ci['ci_low']:.3f}, {s_if_ci['ci_high']:.3f}] |")

    p_gap = p["optimality_gap_valid_only"]
    s_gap = s["optimality_gap_valid_only"]
    lines.append(f"| Opt-gap mean (valid only) | {ci_str(p_gap)} | {ci_str(s_gap)} |")
    lines.append("")
    lines.append("## Per-Instance Results")
    lines.append("")
    lines.append("| ID | n | Baseline obj | Polite result | Polite obj | Polite gap | Strict result | Strict obj | Strict gap |")
    lines.append("|----|---|-------------|---------------|------------|------------|---------------|------------|------------|")

    for rec in per:
        iid = rec["instance_id"]
        n = rec["n_vars"]
        b_obj = f"{rec['baseline_objective']:.6f}"

        def fmt(r):
            if r is None:
                return "N/A", "-", "-"
            if not r.get("valid"):
                err = r.get("error", "?")
                short = err[:35] + "..." if len(err) > 35 else err
                return f"FAIL: {short}", "-", "-"
            return "VALID", f"{r['objective_value']:.4f}", f"{r['optimality_gap']:.4f}"

        ps, po, pg = fmt(rec["polite"])
        ss, so, sg = fmt(rec["strict"])
        lines.append(f"| {iid} | {n} | {b_obj} | {ps} | {po} | {pg} | {ss} | {so} | {sg} |")

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    pn = p["n_instances_valid_format"]
    sn = s["n_instances_valid_format"]
    pg_n = p_gap["n"]
    sg_n = s_gap["n"]
    sg_mean = s_gap["mean"] if s_gap["mean"] is not None else 0
    sg_lo = s_gap["ci_low"] if s_gap["ci_low"] is not None else 0
    sg_hi = s_gap["ci_high"] if s_gap["ci_high"] is not None else 0

    lines.append(
        f"Instruction-following failure is the main finding, not the polite vs strict gap. "
        f"Only {pn}/8 polite and {sn}/8 strict outputs pass format validation. "
        f"Polite returns prose on all 8 instances. Strict has format failures on instances 08 and 09 "
        f"(x-vector length mismatch: 08 strict returned 47 values vs expected 50; 09 strict returned "
        f"104 vs expected 100 -- model miscounted variables, all zeros, infeasible). "
        f"The 95% bootstrap CIs for IF rate overlap heavily "
        f"(polite [{p_if_ci['ci_low']:.3f}, {p_if_ci['ci_high']:.3f}] vs "
        f"strict [{s_if_ci['ci_low']:.3f}, {s_if_ci['ci_high']:.3f}]), so we cannot distinguish "
        f"the two styles on this metric at n=8. Optimality gap numbers are near-meaningless with "
        f"{pg_n} polite and {sg_n} strict valid outputs; the strict mean of {sg_mean:.4f} is dominated "
        f"by one outlier (instance_04, gap=39.0 -- model returned a feasible but suboptimal solution). "
        f"8 instances is not enough to call a direction on optimality gap. "
        f"The actionable item is fixing the run harness so polite prompts produce JSON "
        f"output, not prose -- that is a prompt-wrapper issue in Ryan's lane."
    )
    lines.append("")
    lines.append(
        "Cross-domain note (imagerec pass, commit eee3086): gpt-4o-mini returned the exact same "
        "answer on all 9 image-rec problems regardless of polite vs strict style -- identical label, "
        "count, or relation token in every case. IF rate was 1.0 for both styles, accuracy was "
        "identical per problem. This is a data point, not a style signal, but it adds to the "
        "picture: at n=9, no style effect is detectable on imagerec either."
    )
    lines.append("")

    lines.append("## Data Issues")
    lines.append("")
    lines.append("### Pre-excluded Instances (going-forward rule: any instance where either style truncates is excluded)")
    lines.append("")
    for iid, reason in report["meta"].get("excluded_instances", {}).items():
        lines.append(f"- **instance_{iid}**: {reason}")
    lines.append("")
    if issues:
        lines.append(f"### Format Validation Failures ({len(issues)} output files failed and were excluded from CI)")
        lines.append("")
        for issue in issues:
            lines.append(f"- {issue}")
        lines.append("")
    else:
        lines.append("### Format Validation Failures")
        lines.append("")
        lines.append("None -- all 6 included instances loaded without errors.")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    report = run()

    out_dir = Path("evals/nlp_100_20")
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
    pg = p["optimality_gap_valid_only"]
    sg = s["optimality_gap_valid_only"]
    print(f"\nPolite: IF={p['instruction_following_rate_raw']:.3f} ({p['n_instances_valid_format']}/8)  opt-gap={pg}")
    print(f"Strict: IF={s['instruction_following_rate_raw']:.3f} ({s['n_instances_valid_format']}/8)  opt-gap={sg}")
    print(f"Data issues: {len(report['data_issues'])}")
