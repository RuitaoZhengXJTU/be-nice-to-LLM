#!/usr/bin/env python3
"""
Grading helpers for image-recognition evaluation tasks.
See evals/imagerec/SCORING_DESIGN.md for full design rationale.

Sub-types: single_label_classification (clf), counting (cnt), spatial_relation (spt).

Ground-truth source: COCO val2017, via problem YAMLs in evals/imagerec/problems/.
Design decisions locked in SCORING_DESIGN.md (commit 9babcf1):
  - clf: top-1 exact match, case-insensitive, strip whitespace.
  - cnt: exact integer match as primary metric; count_within_one (|pred-gt|<=1) as secondary.
  - spt: token-exact match against ALLOWED_RELATIONS (closed vocabulary).

Note on spt token set: the problem YAMLs use space-separated tokens ("left of", "right of")
not underscores. ALLOWED_RELATIONS matches the actual YAML ground_truth values.
"""
import json
from dataclasses import dataclass
from typing import Union

# Canonical vocabulary for spt sub-type. SCORING_DESIGN.md references this as the source of truth.
# Values match the token strings used in the spt_*.yaml problem files (space-separated, not underscores).
ALLOWED_RELATIONS: frozenset = frozenset([
    "above",
    "below",
    "left of",
    "right of",
    "inside",
    "contains",
])


def check_image_format(output: Union[str, dict], spec: dict) -> bool:
    """
    Validate that a model output matches the expected format for this task.

    Parameters
    ----------
    output : str or dict
        Raw model output (JSON string) or already-parsed dict.
        If a string, it will be JSON-parsed; parse failure -> False.
    spec : dict
        Task specification dict; must contain "sub_type" or "task_type".

    Returns
    -------
    bool
        True iff the output is valid JSON, contains the required key for this
        sub_type, and the value has the correct type. False on any failure.
        Never raises.
    """
    try:
        if isinstance(output, str):
            data = json.loads(output)
        else:
            data = output

        if not isinstance(data, dict):
            return False

        sub_type = spec.get("sub_type") or spec.get("task_type", "")

        if sub_type in ("single_label_classification", "clf"):
            return "label" in data and isinstance(data["label"], str)

        elif sub_type in ("counting", "cnt"):
            if "count" not in data:
                return False
            v = data["count"]
            # Require a plain int; reject bool (bool is subclass of int in Python),
            # float, and strings even if they contain digits.
            return isinstance(v, int) and not isinstance(v, bool)

        elif sub_type in ("spatial_relation", "spt"):
            if "relation" not in data:
                return False
            v = data["relation"]
            return isinstance(v, str) and v in ALLOWED_RELATIONS

        return False

    except Exception:
        return False


@dataclass
class CountResult:
    """
    Result for the counting sub-type.

    Attributes
    ----------
    exact : float
        1.0 if pred == ground_truth exactly, else 0.0. Primary scoring metric.
    within_one : bool
        True if |pred - ground_truth| <= 1. Secondary metric per SCORING_DESIGN.
    """
    exact: float
    within_one: bool


def image_accuracy(
    output: dict,
    ground_truth: Union[str, int, dict],
    subtype: str,
) -> Union[float, CountResult]:
    """
    Per-instance accuracy for a validated image-recognition output.

    Caller must call check_image_format first; behaviour is undefined for
    outputs that fail the format check.

    Parameters
    ----------
    output : dict
        Parsed, format-validated agent output.
    ground_truth : str, int, or dict
        Ground-truth answer. Accepts the raw YAML ground_truth sub-dict
        (e.g. {"label": "bear"}) or the bare primitive value.
    subtype : str
        One of "clf"/"single_label_classification",
               "cnt"/"counting",
               "spt"/"spatial_relation".

    Returns
    -------
    float
        For clf and spt: 1.0 (correct) or 0.0 (incorrect).
    CountResult
        For cnt: .exact = 0.0 or 1.0 (primary); .within_one = bool (secondary).
    """
    if subtype in ("single_label_classification", "clf"):
        if isinstance(ground_truth, dict):
            gt = str(ground_truth.get("label", ""))
        else:
            gt = str(ground_truth)
        return 1.0 if output["label"].strip().lower() == gt.strip().lower() else 0.0

    elif subtype in ("counting", "cnt"):
        if isinstance(ground_truth, dict):
            gt_val = ground_truth.get("count", ground_truth)
        else:
            gt_val = ground_truth
        pred = int(output["count"])
        gt_int = int(gt_val)
        exact = 1.0 if pred == gt_int else 0.0
        within_one = abs(pred - gt_int) <= 1
        return CountResult(exact=exact, within_one=within_one)

    elif subtype in ("spatial_relation", "spt"):
        if isinstance(ground_truth, dict):
            gt = str(ground_truth.get("relation", ""))
        else:
            gt = str(ground_truth)
        return 1.0 if output["relation"] == gt else 0.0

    raise ValueError(f"Unknown subtype: {subtype!r}")
