# Reference validation artifacts

These CSV files record the accepted Gurobi 13.0.0 holistic validation described
in `../GUROBI_VALIDATION.md`:

- `holistic_acceptance_checks.csv`: required settings and numerical gates;
- `holistic_coverage.csv`: configured, exercised, transferred, and consumed
  feature evidence;
- `generation_builds_audit.csv`: GTEP generation decisions realized in PCM;
- `storage_builds_audit.csv`: GTEP storage decisions realized in PCM.

They are reference evidence, not runtime inputs. A new run writes fresh copies
under `output_holistic/` and should be compared with these artifacts rather
than assumed identical when solver versions or tie-breaking change.
