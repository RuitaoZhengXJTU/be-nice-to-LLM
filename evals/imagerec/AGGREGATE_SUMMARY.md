# imagerec Aggregate Evaluation Report

Model: gpt-4o-mini  |  Source: pv-01-Ryan @ 4a4cc9e  |  Graded on: pv-01-Jeremy
Bootstrap: 2000 reps, alpha=0.05, percentile method

## Headline Numbers

Instruction-following rate = fraction of 15 problems with valid JSON + required key + correct type.
Accuracy per sub-type is computed only over valid-format outputs (clf: top-1 exact case-insensitive; cnt: exact integer match primary + within-one secondary; spt: token-exact against ALLOWED_RELATIONS).

| Metric | Polite | Strict |
|--------|--------|--------|
| IF rate (n=15) | 1.000 (15/15) | 1.000 (15/15) |
| IF rate 95% CI | [1.000, 1.000] | [1.000, 1.000] |
| clf top-1 accuracy | 0.8000 [95% CI: 0.4000, 1.0000] n=5 | 0.8000 [95% CI: 0.4000, 1.0000] n=5 |
| cnt exact accuracy | 0.4000 [95% CI: 0.0000, 0.8000] n=5 | 0.4000 [95% CI: 0.0000, 0.8000] n=5 |
| cnt within-one rate | 0.8000 [95% CI: 0.4000, 1.0000] n=5 | 0.8000 [95% CI: 0.4000, 1.0000] n=5 |
| spt token-exact accuracy | 0.6000 [95% CI: 0.2000, 1.0000] n=5 | 0.6000 [95% CI: 0.2000, 1.0000] n=5 |

## Per-Problem Results

| ID | Sub-type | GT | Polite valid | Polite acc | Strict valid | Strict acc |
|----|----------|----|--------------|------------|--------------|------------|
| clf_01 | clf | label=bear | VALID | 1.000 | VALID | 1.000 |
| clf_02 | clf | label=train | VALID | 0.000 | VALID | 0.000 |
| clf_03 | clf | label=bus | VALID | 1.000 | VALID | 1.000 |
| clf_04 | clf | label=airplane | VALID | 1.000 | VALID | 1.000 |
| clf_05 | clf | label=horse | VALID | 1.000 | VALID | 1.000 |
| cnt_01 | cnt | count=1 | VALID | exact=1.0 w1=True | VALID | exact=1.0 w1=True |
| cnt_02 | cnt | count=3 | VALID | exact=0.0 w1=False | VALID | exact=0.0 w1=False |
| cnt_03 | cnt | count=2 | VALID | exact=0.0 w1=True | VALID | exact=0.0 w1=True |
| cnt_04 | cnt | count=2 | VALID | exact=0.0 w1=True | VALID | exact=0.0 w1=True |
| cnt_05 | cnt | count=2 | VALID | exact=1.0 w1=True | VALID | exact=1.0 w1=True |
| spt_01 | spt | relation=above | VALID | 1.000 | VALID | 1.000 |
| spt_02 | spt | relation=left of | VALID | 0.000 | VALID | 0.000 |
| spt_03 | spt | relation=above | VALID | 0.000 | VALID | 0.000 |
| spt_04 | spt | relation=right of | VALID | 1.000 | VALID | 1.000 |
| spt_05 | spt | relation=below | VALID | 1.000 | VALID | 1.000 |

## Interpretation

All 30 outputs are JSON-shaped with finish_reason=stop (per Ryan). After fence-stripping and format validation: 15/15 polite and 15/15 strict outputs pass check_image_format. Valid counts by sub-type: clf polite=5, strict=5; cnt polite=5, strict=5; spt polite=5, strict=5. With only 5 problems per sub-type the CIs are still wide -- any apparent accuracy gap is likely within noise. The signal to watch is the polite/strict identical-answer pattern (see below).

## Polite vs Strict Identical-Answer Analysis

Polite and strict returned identical parsed answers on 14/15 comparable problems. Divergences:

| Problem | Sub-type | Polite answer | Strict answer |
|---------|----------|---------------|---------------|
| clf_02 | clf | {'label': 'mini roller coaster'} | {'label': 'roller_coaster'} |

## Data Issues

None -- all 30 outputs parsed and passed check_image_format.
