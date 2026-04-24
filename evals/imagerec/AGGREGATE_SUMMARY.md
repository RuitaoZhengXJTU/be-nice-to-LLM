# imagerec Aggregate Evaluation Report

Model: gpt-4o-mini  |  Source: pv-01-Ryan @ fae616f  |  Graded on: pv-01-Jeremy
Bootstrap: 2000 reps, alpha=0.05, percentile method

## Headline Numbers

Instruction-following rate = fraction of 9 problems with valid JSON + required key + correct type.
Accuracy per sub-type is computed only over valid-format outputs (clf: top-1 exact case-insensitive; cnt: exact integer match primary + within-one secondary; spt: token-exact against ALLOWED_RELATIONS).

| Metric | Polite | Strict |
|--------|--------|--------|
| IF rate (n=9) | 1.000 (9/9) | 1.000 (9/9) |
| IF rate 95% CI | [1.000, 1.000] | [1.000, 1.000] |
| clf top-1 accuracy | 0.6667 [95% CI: 0.0000, 1.0000] n=3 | 0.6667 [95% CI: 0.0000, 1.0000] n=3 |
| cnt exact accuracy | 0.3333 [95% CI: 0.0000, 1.0000] n=3 | 0.3333 [95% CI: 0.0000, 1.0000] n=3 |
| cnt within-one rate | 0.6667 [95% CI: 0.0000, 1.0000] n=3 | 0.6667 [95% CI: 0.0000, 1.0000] n=3 |
| spt token-exact accuracy | 0.3333 [95% CI: 0.0000, 1.0000] n=3 | 0.3333 [95% CI: 0.0000, 1.0000] n=3 |

## Per-Problem Results

| ID | Sub-type | GT | Polite valid | Polite acc | Strict valid | Strict acc |
|----|----------|----|--------------|------------|--------------|------------|
| clf_01 | clf | label=bear | VALID | 1.000 | VALID | 1.000 |
| clf_02 | clf | label=train | VALID | 0.000 | VALID | 0.000 |
| clf_03 | clf | label=bus | VALID | 1.000 | VALID | 1.000 |
| cnt_01 | cnt | count=1 | VALID | exact=1.0 w1=True | VALID | exact=1.0 w1=True |
| cnt_02 | cnt | count=3 | VALID | exact=0.0 w1=False | VALID | exact=0.0 w1=False |
| cnt_03 | cnt | count=2 | VALID | exact=0.0 w1=True | VALID | exact=0.0 w1=True |
| spt_01 | spt | relation=above | VALID | 1.000 | VALID | 1.000 |
| spt_02 | spt | relation=left of | VALID | 0.000 | VALID | 0.000 |
| spt_03 | spt | relation=above | VALID | 0.000 | VALID | 0.000 |

## Interpretation

All 18 outputs are JSON-shaped with finish_reason=stop (per Ryan). After fence-stripping and format validation: 9/9 polite and 9/9 strict outputs pass check_image_format. Valid counts by sub-type: clf polite=3, strict=3; cnt polite=3, strict=3; spt polite=3, strict=3. With only 3 problems per sub-type the CIs are very wide -- any style gap visible here is within noise. More problems per sub-type are needed before drawing conclusions about polite vs strict accuracy.

## Data Issues

None -- all 18 outputs parsed and passed check_image_format.
