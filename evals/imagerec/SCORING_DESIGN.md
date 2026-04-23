# Image Recognition Grading Design Note

Author: Jeremy
Date: 2026-04-22
Status: Final -- design decisions locked, Ryan can generate instances

## What This Document Is

A scoping note for the grading side of image recognition as a second evaluation domain.
No task instances are included here; Ryan will generate those once scoring is agreed upon.

## Task Sub-types and Correctness Criteria

Three natural sub-types, each with a different correctness definition:

### 1. Single-label Classification

- **Prompt asks**: "What is the primary object in this image? Return JSON: {\"label\": \"...\"}."
- **Correct**: exact string match against ground-truth label (case-insensitive, strip whitespace).
- **Metric analogous to optimality_gap**: `label_error = 1 - exact_match` (binary per instance).
  Across instances: mean label_error + 95% bootstrap CI.

### 2. Object Counting

- **Prompt asks**: "How many [object] are in the image? Return JSON: {\"count\": <integer>}."
- **Correct (primary)**: exact integer match.
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

Required additions to the grading infrastructure (see grade_image.py in this directory):

- `check_image_format(output, spec)` -- validates required key is present and correctly typed.
- `image_accuracy(output, ground_truth, subtype)` -- returns float in [0, 1] (1.0 = fully correct).

The bootstrap CI logic in compare_results.py is reusable as-is for image tasks.

## Design Decisions (locked -- unblocks Ryan)

Three questions were flagged as open in the draft. Decisions below.

**1. Top-k tolerance for single-label**
Use top-1 strict match for v1. The primary metric is exact match on the `label` field.
Top-5 tolerance can be added as a secondary column in the output JSON later if exact-match
rates are too low to distinguish styles. For now, top-1 strict keeps grading unambiguous.

**2. Counting tolerance**
Use exact integer match as the primary correctness criterion (count_error = 0 iff exact).
The output JSON will also include a secondary flag `count_within_one` (bool) for cases where
|pred - gt| <= 1. Report both in compare_multi output; use exact match for the headline CI.
Rationale: occlusion and truncation make +/-1 meaningful, but we need an unambiguous primary.

**3. Image delivery to the model**
Use public URL. COCO val2017 images are accessible at
`http://images.cocodataset.org/val2017/<filename>`. No base64 encoding needed for GPT-4V
and similar models that accept URL inputs. If a model does not support URL inputs, the
harness (Ryan's lane) can download and encode on-the-fly; the grading layer does not change.
