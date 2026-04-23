# NLP_100_20 Aggregate Evaluation Report

Model: gpt-4o-mini  |  Source: pv-01-Ryan @ 0da7d64  |  Graded on: pv-01-Jeremy
Bootstrap: 2000 reps, alpha=0.05, percentile method

## Headline Numbers

Instruction-following rate = fraction of 6 instances (01-06) with valid JSON + correct x-vector length + numeric objective.
instance_07 is pre-excluded (see Data Issues below). Optimality gap = |obj_agent - obj_baseline| / |obj_baseline| (computed only over valid-format outputs).

| Metric | Polite | Strict |
|--------|--------|--------|
| IF rate (n=6) | 0.167 (1/6) | 0.333 (2/6) |
| IF rate 95% CI | [0.000, 0.500] | [0.000, 0.667] |
| Opt-gap mean (valid only) | 0.0000 [95% CI: 0.0000, 0.0000] n=1 | 19.5000 [95% CI: 0.0000, 39.0000] n=2 |

## Per-Instance Results

| ID | n | Baseline obj | Polite result | Polite obj | Polite gap | Strict result | Strict obj | Strict gap |
|----|---|-------------|---------------|------------|------------|---------------|------------|------------|
| 01 | 100 | 0.000000 | FAIL: JSONDecodeError: Expecting value: l... | - | - | FAIL: x length 108 != expected 100 | - | - |
| 02 | 100 | -316.227766 | FAIL: JSONDecodeError: Expecting value: l... | - | - | FAIL: x length 98 != expected 100 | - | - |
| 03 | 100 | 0.000000 | VALID | 0.0000 | 0.0000 | VALID | 0.0000 | 0.0000 |
| 04 | 10 | 0.100000 | FAIL: JSONDecodeError: Expecting value: l... | - | - | VALID | 4.0000 | 39.0000 |
| 05 | 50 | 4.133333 | FAIL: JSONDecodeError: Expecting value: l... | - | - | FAIL: x length 48 != expected 50 | - | - |
| 06 | 100 | 31.516667 | FAIL: JSONDecodeError: Expecting value: l... | - | - | FAIL: x length 123 != expected 100 | - | - |

## Interpretation

Instruction-following failure is the main finding, not the polite vs strict gap. Only 1/6 polite and 2/6 strict outputs pass format validation -- both styles are producing prose explanations rather than bare JSON for most instances. The 95% bootstrap CIs for IF rate overlap heavily (polite [0.000, 0.500] vs strict [0.000, 0.667]), so we cannot distinguish the two styles on this metric at n=6. Optimality gap numbers are near-meaningless with 1 polite and 2 strict valid outputs; the strict mean of 19.5000 is dominated by one outlier (instance_04, gap=39.0 -- model returned a feasible but suboptimal solution). 6 instances is not enough to call a direction on optimality gap even if the harness produces valid JSON. The actionable item is fixing the run harness so polite prompts produce JSON output, not prose -- that is a prompt-wrapper issue in Ryan's lane.

## Data Issues

### Pre-excluded Instances (going-forward rule: any instance where either style truncates is excluded)

- **instance_07**: gpt-4o-mini hard cap is max_tokens=16384; strict output truncates mid-vector at that cap, polite returns prose instead of JSON. Re-run at max_tokens=16384 still truncates (pv-01-Ryan@0da7d64). Going-forward rule: any instance where either style truncates is excluded from aggregate scoring.

### Format Validation Failures (9 output files failed and were excluded from CI)

- instance_01_polite: load failed -- JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- instance_01_strict: format check failed -- x length 108 != expected 100
- instance_02_polite: load failed -- JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- instance_02_strict: format check failed -- x length 98 != expected 100
- instance_04_polite: load failed -- JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- instance_05_polite: load failed -- JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- instance_05_strict: format check failed -- x length 48 != expected 50
- instance_06_polite: load failed -- JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- instance_06_strict: format check failed -- x length 123 != expected 100
