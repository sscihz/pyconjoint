# Data fixtures

- `immigrationconjoint.csv` is exported from the CRAN `cjoint` package
  dataset (`immigrationconjoint`) via base R `write.csv` on 2026-02-05.
- `immigrationconjoint_levels.json` stores the original factor levels to
  restore categorical ordering when reading the CSV.
- `immigrationconjoint_weights.csv` contains deterministic `runif()` weights
  generated with `set.seed(42)` for parity tests against the R implementation.
- `cjoint_expected_results.json` contains cjoint summary outputs used by tests.
- Source repo: https://github.com/cran/cjoint

This dataset is used for PyJoint regression and cross-check tests.
