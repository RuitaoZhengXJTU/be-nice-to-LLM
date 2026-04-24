# NLP_100_20 Aggregate Evaluation Report

Model: gpt-4o-mini  |  Source: pv-01-Ryan @ b564a85  |  Graded on: pv-01-Jeremy
Bootstrap: 2000 reps, alpha=0.05, percentile method

## Headline Numbers

Instruction-following rate = fraction of 8 instances (01-06, 08, 09) with valid JSON + correct x-vector length + numeric objective.
instance_07 and instance_10 are pre-excluded (see Data Issues below). Optimality gap = |obj_agent - obj_baseline| / |obj_baseline| (computed only over valid-format outputs).

| Metric | Polite | Strict |
|--------|--------|--------|
| IF rate (n=8) | 0.125 (1/8) | 0.250 (2/8) |
| IF rate 95% CI | [0.000, 0.375] | [0.000, 0.625] |
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
| 08 | 50 | 19.250000 | FAIL: missing x or objective_value key | - | - | FAIL: x length 47 != expected 50 | - | - |
| 09 | 100 | 143.500000 | FAIL: missing x or objective_value key | - | - | FAIL: x length 104 != expected 100 | - | - |

## Interpretation

Instruction-following failure is the main finding, not the polite vs strict gap. Only 1/8 polite and 2/8 strict outputs pass format validation. Polite returns prose on all 8 instances. Strict has format failures on instances 08 and 09 (x-vector length mismatch: 08 strict returned 47 values vs expected 50; 09 strict returned 104 vs expected 100 -- model miscounted variables, all zeros, infeasible). The 95% bootstrap CIs for IF rate overlap heavily (polite [0.000, 0.375] vs strict [0.000, 0.625]), so we cannot distinguish the two styles on this metric at n=8. Optimality gap numbers are near-meaningless with 1 polite and 2 strict valid outputs; the strict mean of 19.5000 is dominated by one outlier (instance_04, gap=39.0 -- model returned a feasible but suboptimal solution). 8 instances is not enough to call a direction on optimality gap. The actionable item is fixing the run harness so polite prompts produce JSON output, not prose -- that is a prompt-wrapper issue in Ryan's lane.

Cross-domain note (imagerec pass, commit eee3086): gpt-4o-mini returned the exact same answer on all 9 image-rec problems regardless of polite vs strict style -- identical label, count, or relation token in every case. IF rate was 1.0 for both styles, accuracy was identical per problem. This is a data point, not a style signal, but it adds to the picture: at n=9, no style effect is detectable on imagerec either.

## Data Issues

### Pre-excluded Instances (going-forward rule: any instance where either style truncates is excluded)

- **instance_07**: 200-var problem. gpt-4o-mini hard cap is max_tokens=16384; strict output truncates mid-vector at that cap, polite returns prose. Re-run at max_tokens=16384 still truncates (pv-01-Ryan@0da7d64). Going-forward rule: any instance where either style truncates is excluded from aggregate scoring.
- **instance_10**: 150-var problem. gpt-4o-mini hard cap is max_tokens=16384; strict output truncates at that cap (finish_reason=length), polite returns prose. Documented in pv-01-Ryan@b564a85. Same going-forward exclusion rule as instance_07.

### Format Validation Failures (13 output files failed and were excluded from CI)

- instance_01_polite: load failed -- JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- instance_01_strict: format check failed -- x length 108 != expected 100
- instance_02_polite: load failed -- JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- instance_02_strict: format check failed -- x length 98 != expected 100
- instance_04_polite: load failed -- JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- instance_05_polite: load failed -- JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- instance_05_strict: format check failed -- x length 48 != expected 50
- instance_06_polite: load failed -- JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- instance_06_strict: format check failed -- x length 123 != expected 100
- instance_08_polite: format check failed -- missing x or objective_value key
- instance_08_strict: format check failed -- x length 47 != expected 50
- instance_09_polite: format check failed -- missing x or objective_value key
- instance_09_strict: format check failed -- x length 104 != expected 100
