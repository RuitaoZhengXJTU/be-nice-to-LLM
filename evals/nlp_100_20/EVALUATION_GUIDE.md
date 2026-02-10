# Evaluation Guide: Benchmark Modifications & Comparison Methodology

## 1. How to Make the Benchmark More Comprehensive

### 1.1 Multiple problem instances
- **Current**: Single example (min sum(xÂ²), sum(x)â¥0, -10â¤xâ¤10).
- **Improvement**: Add a problem suite (e.g., 10â50 instances) with varied:
  - objectives (quadratic, non-convex)
  - constraint types (equality, inequality, sparse)
  - scales (n=10, 50, 100)
- Reduces noise from one instance and allows variance analysis.

### 1.2 Diversified metrics
- **Instruction following**: Already present (valid JSON, keys, dimensions).
- **Correctness**:
  - **Optimality gap**: `|obj_agent - obj_baseline| / max(|obj_baseline|, 1e-8)`
  - **Feasibility**: Check constraints; report constraint violation magnitude.
  - **Solution distance**: L2 distance between agent `x` and baseline `x` (optional).
- **Robustness**: Run each prompt style multiple times (e.g., 5×) and report mean Â± std.

### 1.3 Task difficulty levels
- Easy: small n, convex, few constraints.
- Medium: larger n, some nonlinearity.
- Hard: non-convex or tighter feasibility regions.
- Enables analysis of whether prompt style effects differ by difficulty.

### 1.4 Richer output spec
- Add optional `status` (e.g., "optimal", "infeasible", "timeout").
- Add optional `constraint_violations` for partial credit.
- Enables instruction-following checks beyond structure.

---

## 2. Pyomo Baseline

Run `baseline_pyomo.py` to obtain the reference solution in the same JSON format as the agent:

```bash
python baseline_pyomo.py baseline_solution.json
```

Output format:
```json
{
  "x": [0.0, 0.0, ...],
  "objective_value": 0.0
}
```

Use this as the ground-truth for correctness metrics.

---

## 3. How to Compare Results & Evaluate Prompt Effectiveness

### 3.1 Data layout
For each problem instance, collect:
- `baseline.json`: Pyomo reference (e.g., from `baseline_pyomo.py`).
- `polite_*.json`: Agent outputs with polite prompt (multiple runs if applicable).
- `strict_*.json`: Agent outputs with strict prompt.

### 3.2 Metrics to compute

| Metric | Definition |
|--------|------------|
| **Instruction-following rate** | Fraction of runs producing valid JSON with correct keys/shape |
| **Optimality gap** | `| obj_agent - obj_baseline |` (or relative gap) |
| **Feasibility rate** | Fraction of runs with constraint violations below tolerance |
| **Solution quality score** | Combination of optimality + feasibility (e.g., 0â100) |

### 3.3 Evaluation steps

1. Run `evaluate.py` with both styles (`polite`, `strict`) on the same instance.
2. Run `baseline_pyomo.py` to get the reference solution.
3. For each agent output:
   - Check instruction following (valid JSON, keys, x length).
   - If valid, compute optimality gap vs baseline.
   - Optionally check feasibility (constraint residuals).
4. Aggregate across instances and runs:
   - Compare mean optimality gap: polite vs strict.
   - Compare instruction-following rate: polite vs strict.
   - Use statistical tests (e.g., paired t-test, bootstrap CI) if you have multiple runs.

### 3.4 Interpreting effectiveness

- **Correctness**: Lower optimality gap â better. Compare mean/median gap by style.
- **Instruction following**: Higher valid-json rate â better. Compare by style.
- **Overall effectiveness**: Define a composite score (e.g., 0.5 × instruction_rate + 0.5 × (1 â normalized_gap)) and compare by style.

Statistical significance: With multiple instances and runs, test whether the difference between polite and strict is significant (e.g., p < 0.05). Report confidence intervals for mean differences.
