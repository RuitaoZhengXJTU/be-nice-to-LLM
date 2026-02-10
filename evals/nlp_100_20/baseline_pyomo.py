#!/usr/bin/env python3
"""
Pyomo baseline solver for nlp_100_20.
Solves the same nonlinear problem as the agent eval and outputs JSON in the same format.
Problem: minimize sum(x[i]^2) s.t. sum(x) >= 0 (x20), -10 <= x[i] <= 10.
"""
import json
from pyomo.environ import ConcreteModel, Var, Objective, Constraint, minimize
from pyomo.opt import SolverFactory


def build_model():
    """Build the nlp_100_20 model: min sum(x^2) s.t. sum(x)>=0, -10<=x<=10."""
    m = ConcreteModel()
    n = 100
    m.I = range(n)
    m.x = Var(m.I, bounds=(-10, 10), initialize=0)
    m.obj = Objective(expr=sum(m.x[i] ** 2 for i in m.I), sense=minimize)
    # 20 identical constraints: sum(x) >= 0
    m.con = Constraint(
        range(20),
        rule=lambda mdl, j: sum(mdl.x[i] for i in mdl.I) >= 0,
    )
    return m


def solve_and_export_json(out_path: str | None = None) -> dict:
    """Solve the model and return/export solution as JSON matching agent output format."""
    m = build_model()
    opt = SolverFactory("ipopt")
    if not opt.available():
        raise RuntimeError("IPOPT not available. Install: conda install -c conda-forge ipopt")
    results = opt.solve(m, tee=False)
    x_vals = [round(float(m.x[i].value), 6) for i in m.I]
    obj_val = round(float(m.obj()), 6)
    out = {"x": x_vals, "objective_value": obj_val}
    if out_path:
        with open(out_path, "w") as f:
            json.dump(out, f, indent=2)
    return out


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "baseline_solution.json"
    out = solve_and_export_json(path)
    print(json.dumps(out, indent=2))
