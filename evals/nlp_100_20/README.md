# Primary task: Nonlinear programming (100 vars, 20 constraints)

One example evaluation benchmark for the politeness-vs-strictness meta-study.

**Task**: Solve a nonlinear programming problem with 100 variables and 20 constraints, and return the solution (optimal variable values and objective value).

**Purpose**: Compare the same agent's effectiveness when the *only* change is prompt style (polite vs strict). Task content is fixed; we measure correctness and instruction following.

**Expected output format**: JSON with keys `x` (list of 100 floats), `objective_value` (float), and optionally `status` (e.g. "optimal", "infeasible").

**Evaluation**:
- Correctness: compare objective value (and optionally solution) to a reference solver or golden instance.
- Instruction following: output is valid JSON with required keys and dimensions.

See `task_spec.yaml`, `prompts/`, and `evaluate.py`.
