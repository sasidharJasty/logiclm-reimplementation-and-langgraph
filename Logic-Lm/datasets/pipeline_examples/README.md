# Logic pipeline examples

The JSONL files in this directory are small, deterministic smoke-test sets.
Each record contains the natural-language problem, the intended pipeline, a
solver/dataset reference, and the expected symbolic formulation or result.

The splits are deliberately disjoint and contain examples for LP, FOL, CSP,
and SAT so that adding a new pipeline does not silently go untested.
