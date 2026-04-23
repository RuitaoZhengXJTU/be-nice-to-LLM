# Image Recognition Grading Design Note

Author: Jeremy
Date: 2026-04-22
Status: Draft -- awaiting scoring agreement before Ryan generates instances

## What This Document Is

A scoping note for the grading side of image recognition as a second evaluation domain.
No task instances are included here; Ryan will generate those once scoring is agreed upon.

## Task Sub-types and Correctness Criteria

Three natural sub-types, each with a different correctness definition:

### 1. Single-label Classification

- **Prompt asks**: "What is the primary object in this image? Return JSON: {\"label\": \"...\"}."
- **Correct**: exact string match against ground-truth label (case-insensitive, strip whitespace).
  For top-k tolerance: correct if ground-truth is in agent's top-k list.
- **Metric analogous to optimality_gap**: `label_error = 1 - exact_match` (binary per instance).
  Across instances: mean label_error + 95% bootstrap CI.

### 2. Object Counting

- **Prompt asks**: "How many [object] are in the image? Return JSON: {\"count\": <integer>}."
- **Correct**: exact integer match, or within tolerance T (e.g., |pred - gt| <= 1 for small counts).
- **Metric**: `count_error = |pred_count - gt_count| / max(gt_count, 1)`.
  Directly analogous to optimality_gap in compare_results.py.

### 3. Spatial / Relational

- **Prompt asks**: "Describe the spatial relationship between A and B. Return JSON: {\"relation\": \"...\"}."
- **Correct**: exact match against a closed vocabulary (e.g., "left of", "above", "behind").
  Open-vocab descriptions are hard to grade automatically; restrict to closed-vocab for v1.
- **Metric**: binary correct/incorrect per instance; mean + CI across instances.

## Ground-Truth Sources

Preference order:

1. **COCO val2017** -- bounding boxes and category labels are public; counting and spatial
   relations are derivable from the annotations. No licence issues for research use.
2. **ImageNet val** -- single-label only; large and well-known, good fallback.
3. Manually labeled mini-set -- only if COCO/ImageNet do not cover a needed sub-type.

For v1, stay on COCO val2017 so all three sub-types can share one image pool.

## Integration with compare_results Format

The existing compare_results.py expects per-instance JSON with keys `x` and `objective_value`.
For image tasks the analogous output schema is:

```json
{
  "label": "...",
  "count": 0,
  "relation": "...",
  "instruction_following": true
}
```

Only the key relevant to the sub-type needs to be present.

Required additions to the grading infrastructure:

- `check_image_format(data, task_type)` -- validates required key is present and correctly typed.
- `image_accuracy(pred, gt, task_type, tol=1)` -- returns float in [0, 1] (1.0 = fully correct).

These can live in a new `evals/image_rec/grade_image.py` that mirrors compare_results.py's interface.
The bootstrap CI logic added to compare_results.py (this commit) is reusable as-is for image tasks.

## Open Questions (not blocking v1)

- Top-k tolerance for single-label: use top-1 strict for v1, add top-5 as secondary metric later.
- Counting tolerance: start with exact match, flag +/-1 as a variant in the output JSON.
- Image delivery to the model: URL vs base64. COCO images are publicly accessible by URL; prefer URL.
- Whether to include adversarial/ambiguous images: defer to later, keep v1 unambiguous.
