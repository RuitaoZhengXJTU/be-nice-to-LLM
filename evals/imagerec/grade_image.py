#!/usr/bin/env python3
"""
Grading helpers for image-recognition evaluation tasks.
See evals/imagerec/SCORING_DESIGN.md for full design rationale.

Sub-types: single-label classification, object counting, spatial/relational.
"""


def check_image_format(output: dict, spec: dict) -> bool:
    """
    Validate that the agent output matches the expected format for this task.

    Parameters
    ----------
    output : dict
        Parsed agent output JSON.
    spec : dict
        Task specification dict; must contain at least {"subtype": str} where
        subtype is one of "single_label", "counting", or "spatial".

    Returns
    -------
    bool
        True if output is valid for the given subtype, False otherwise.

    Raises
    ------
    NotImplementedError
        Implementation pending after Ryan finalizes task instances.
    """
    raise NotImplementedError


def image_accuracy(output: dict, ground_truth: dict, subtype: str) -> float:
    """
    Compute per-instance accuracy for an image recognition task.

    Parameters
    ----------
    output : dict
        Parsed agent output JSON (validated by check_image_format first).
    ground_truth : dict
        Ground-truth record from COCO val2017 or equivalent source.
    subtype : str
        One of "single_label", "counting", or "spatial".

    Returns
    -------
    float
        Accuracy score in [0.0, 1.0] where 1.0 = fully correct.
        For single_label and spatial: binary (0 or 1).
        For counting: 1 - count_error (clamped to [0, 1]).

    Raises
    ------
    NotImplementedError
        Implementation pending after Ryan finalizes task instances.
    """
    raise NotImplementedError
