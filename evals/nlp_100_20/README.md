# Primary task: Nonlinear programming (variable dimensions)

One evaluation benchmark for the politeness-vs-strictness meta-study.

**Task**: Solve a nonlinear programming problem and return the solution (optimal variable values and objective value). Problem dimensions (number of variables and constraints) vary by instance to better reflect model effectiveness.

**Instances** (see `problems/problem_manifest.yaml` and `problems/instance_XX.txt`):

| Instance   | Variables | Constraints | Description |
|-----------|-----------|-------------|-------------|
| instance_01 | 100 | 20 | Minimize sum of squares; sum >= 0 (repeated). |
| instance_02 | 100 | 20 | Minimize sum of x; sum of squares <= 1000. |
| instance_03 | 100 | 20 | Minimize sum of (x-1)^2; sum >= 0. |
| instance_04 | 10  | 3  | Small: mixed linear/quadratic constraints. |
| instance_05 | 50  | 15 | Medium: penalized deviation from i/50. |
| instance_06 | 100 | 30 | More constraints; quadratic terms in constraints. |
| instance_07 | 200 | 25 | Larger: 200 vars, sum-of-squares minus linear. |

**Purpose**: Compare the same agent's effectiveness when the *only* change is prompt style (polite vs strict). We measure instruction following (valid JSON, correct vector length) and correctness (objective value).

**Usage**:
- Run one instance: `python run_openai_eval.py instance_04`
- Run all instances: `python run_openai_eval.py all`
- Outputs: `outputs/<instance_id>_<polite|strict>_output.json`

See `task_spec.yaml`, `prompts/`, and `evaluate.py` for the core eval logic.
