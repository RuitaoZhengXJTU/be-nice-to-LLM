# NLP_100_20 Aggregate Evaluation Report

Model: gpt-4o-mini  |  Source: pv-01-Ryan @ 69929ac  |  Graded on: pv-01-Jeremy
Bootstrap: 2000 reps, alpha=0.05, percentile method

## Headline Numbers

Instruction-following rate = fraction of 7 instances with valid JSON + correct x-vector length + numeric objective.
Optimality gap = |obj_agent - obj_baseline| / |obj_baseline| (computed only over valid-format outputs).

| Metric | Polite | Strict |
|--------|--------|--------|
| IF rate (n=7) | 0.143 (1/7) | 0.286 (2/7) |
| IF rate 95% CI | [0.000, 0.429] | [0.000, 0.571] |
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
| 07 | 200 | 27.625000 | FAIL: JSONDecodeError: Expecting value: l... | - | - | FAIL: JSONDecodeError: Expecting value: l... | - | - |

## Interpretation

Instruction-following failure is the main finding, not the polite vs strict gap. Only 1/7 polite and 2/7 strict outputs pass format validation -- both styles are producing prose explanations rather than bare JSON for most instances. The 95% bootstrap CIs for IF rate overlap heavily (polite [0.000, 0.429] vs strict [0.000, 0.571]), so we cannot distinguish the two styles on this metric at n=7. Optimality gap numbers are near-meaningless with 1 polite and 2 strict valid outputs; the strict mean of 19.5000 is dominated by one outlier (instance_04, gap=39.0 -- model returned a feasible but suboptimal solution). 7 instances is not enough to call a direction on optimality gap even if the harness produces valid JSON. The actionable item is fixing the run harness so polite prompts produce JSON output, not prose -- that is a prompt-wrapper issue in Ryan's lane.

## Data Issues

11 output files failed validation and were excluded from aggregate CI:

- instance_01_polite: load failed -- JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- instance_01_strict: format check failed -- x length 108 != expected 100
- instance_02_polite: load failed -- JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- instance_02_strict: format check failed -- x length 98 != expected 100
- instance_04_polite: load failed -- JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- instance_05_polite: load failed -- JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- instance_05_strict: format check failed -- x length 48 != expected 50
- instance_06_polite: load failed -- JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- instance_06_strict: format check failed -- x length 123 != expected 100
- instance_07_polite: load failed -- JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- instance_07_strict: load failed -- JSONDecodeError: Expecting value: line 1 column 1 (char 0)
