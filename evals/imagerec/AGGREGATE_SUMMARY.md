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

## Multi-Seed Analysis (seeds: baseline, 17, 42; baseline@4a4cc9e, seed runs@347ab63)

Total cells: 90 (15 problems x 2 styles x 3 seeds). Single-seed headline numbers above are unchanged; this section extends the picture.

### (a) Pooled Accuracy by Sub-type

n = 5 problems x 3 seeds = 15 per (style, sub-type). Bootstrap CI over 15 accuracy values (or fewer if format failures).

| Metric | Polite | Strict |
|--------|--------|--------|
| IF rate (45 cells/style) | 1.000 (45/45) | 1.000 (45/45) |
| clf top-1 accuracy (pooled) | 0.8000 [95% CI: 0.6000, 1.0000] n=15 | 0.8000 [95% CI: 0.6000, 1.0000] n=15 |
| cnt exact accuracy (pooled) | 0.4000 [95% CI: 0.1333, 0.6667] n=15 | 0.5333 [95% CI: 0.2667, 0.8000] n=15 |
| cnt within-one rate (pooled) | 0.8000 [95% CI: 0.6000, 1.0000] n=15 | 0.8000 [95% CI: 0.6000, 1.0000] n=15 |
| spt token-exact accuracy (pooled) | 0.6000 [95% CI: 0.3333, 0.8667] n=15 | 0.6667 [95% CI: 0.4667, 0.8667] n=15 |

### (b) Across-Seed Answer Stability

For each (problem, style), do all 3 seeds return the same parsed answer? Polite: 14/15 stable. Strict: 13/15 stable.

**Polite unstable problems:**

| Problem | Sub-type | baseline | seed17 | seed42 |
|---------|----------|----------|--------|--------|
| clf_02 | clf | {'label': 'mini roller coaster'} | {'label': 'roller_coaster'} | {'label': 'roller_coaster'} |

**Strict unstable problems:**

| Problem | Sub-type | baseline | seed17 | seed42 |
|---------|----------|----------|--------|--------|
| cnt_04 | cnt | {'count': 1} | {'count': 2} | {'count': 2} |
| spt_02 | spt | {'relation': 'right of'} | {'relation': 'right of'} | {'relation': 'left of'} |

### (c) Cross-Seed Polite=Strict Identical-Answer Rate

Out of 45 (problem, seed) pairs, polite and strict returned the same parsed answer on 41 (0.911).

Per-problem breakdown for problems with < 3/3 identical seeds:

**clf_02** (clf): 2/3 seeds identical
  - seed=baseline: polite={'label': 'mini roller coaster'}  !=  strict={'label': 'roller_coaster'}
  - seed=17: polite={'label': 'roller_coaster'}  =  strict={'label': 'roller_coaster'}
  - seed=42: polite={'label': 'roller_coaster'}  =  strict={'label': 'roller_coaster'}

**cnt_04** (cnt): 1/3 seeds identical
  - seed=baseline: polite={'count': 1}  =  strict={'count': 1}
  - seed=17: polite={'count': 1}  !=  strict={'count': 2}
  - seed=42: polite={'count': 1}  !=  strict={'count': 2}

**spt_02** (spt): 2/3 seeds identical
  - seed=baseline: polite={'relation': 'right of'}  =  strict={'relation': 'right of'}
  - seed=17: polite={'relation': 'right of'}  =  strict={'relation': 'right of'}
  - seed=42: polite={'relation': 'right of'}  !=  strict={'relation': 'left of'}

## Data Issues

None -- all 30 outputs parsed and passed check_image_format.
