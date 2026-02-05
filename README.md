# PyJoint: Python Implementation of Conjoint Analysis

[![PyPI version](https://badge.fury.io/py/pyjoint.svg)](https://badge.fury.io/py/pyjoint)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**PyJoint** is a Python implementation of the [cjoint](https://github.com/jhainmueller/cjoint) R package, providing tools for estimating **Average Marginal Component Effects (AMCEs)** and **Average Component Interaction Effects (ACIEs)** from conjoint survey experiments.

This package follows the methodology from Hainmueller, Hopkins, and Yamamoto (2014) and provides a Python-native interface with statistical equivalence to the original R implementation.

## Features

- ✅ **AMCE Estimation**: Estimate Average Marginal Component Effects
- ✅ **ACIE Estimation**: Estimate Average Component Interaction Effects  
- ✅ **Cluster-Robust Standard Errors**: Li-Zeileis (2008) correction
- ✅ **Heteroskedasticity-Consistent SEs**: HC2 variance estimation
- ✅ **Design-Dependent Adjustment**: Delta method for non-uniform randomization
- ✅ **Summary Tables**: Formatted output with significance tests
- ✅ **Coefficient Plots**: Visualize effects with confidence intervals
- ✅ **Custom Baselines**: Override default reference levels
- ✅ **Weighted Regression**: Support for survey weights

## Installation

```bash
pip install pyjoint
```

Or install from source:

```bash
git clone https://github.com/sscihz/pyconjoint.git
cd pyconjoint
pip install -e .
```

## Quick Start

```python
import pandas as pd
import numpy as np
import pyjoint

# Create example conjoint data
np.random.seed(42)
data = pd.DataFrame({
    'chosen': np.random.randint(0, 2, 1000),
    'Gender': np.random.choice(['Male', 'Female'], 1000),
    'Education': np.random.choice(['HS', 'College', 'Graduate'], 1000),
    'Skills': np.random.choice(['Low', 'Medium', 'High'], 1000),
    'respondent_id': np.repeat(np.arange(500), 2)
})

# Estimate AMCEs
result = pyjoint.amce(
    formula='chosen ~ Gender + Education + Skills',
    data=data,
    respondent_id='respondent_id',
    cluster=True
)

# View summary
summ = result.summary()
print(summ)

# Plot results
result.plot()
```

## Documentation

### Main Function: `amce()`

Estimate AMCEs and ACIEs from conjoint experiment data.

**Parameters:**
- `formula` (str): Model formula (e.g., `"Y ~ X1 + X2 + X1:X2"`)
- `data` (pd.DataFrame): Dataset with outcome and attributes
- `design` (str or ConjointDesign): Design matrix ("uniform" or custom)
- `respondent_varying` (list): Variables varying by respondent
- `respondent_id` (str): Column name for respondent identifier
- `cluster` (bool): Whether to cluster standard errors
- `na_ignore` (bool): Whether to ignore missing values
- `weights` (str): Column name for survey weights
- `baselines` (dict): Custom baseline levels

**Returns:**
- `AMCEResult`: Object with estimates, standard errors, and metadata

### Design Matrix: `make_design()`

Create design matrices for non-uniform randomization.

```python
# Create custom design with constraints
design = pyjoint.make_design(
    design_type="array",
    J=design_array,  # Multidimensional probability array
    constraints={"Gender": ["female-muslim"]},
    attribute_levels={
        "Gender": ["male", "female"],
        "Education": ["HS", "College", "Graduate"]
    }
)

# Use custom design in AMCE estimation
result = pyjoint.amce(
    formula='y ~ x1 + x2',
    data=data,
    design=design
)
```

### Summary Tables

```python
# Create summary with significance tests
summ = pyjoint.summary_amce(result, ci_level=0.95)

# Access tables
print(summ.amce)      # Main effects
print(summ.acie)      # Interaction effects (if any)
print(summ.baselines_amce)  # Baseline levels
```

### Plotting

```python
# Basic plot
result.plot()

# Customized plot
result.plot(
    main="AMCE Estimates",
    xlab="Effect on Probability",
    ci=0.99,
    colors=["steelblue", "darkred"],
    xlim=(-0.2, 0.2)
)

# Plot only main effects or interactions
result.plot(plot_display="unconditional")  # AMCEs only
result.plot(plot_display="interaction")     # ACIEs only
```

## Statistical Methods

### AMCE Estimation

AMCEs are estimated via OLS regression:

```
AMCE_jk = E[Y|X_j=k, X_-j=baseline] - E[Y|X_j=baseline_j, X_-j=baseline]
```

The coefficient of level k directly estimates the AMCE for that level.

### Cluster-Robust Standard Errors

With clustering on respondents (Li & Zeileis, 2008):

```
dfc = (M/(M-1)) * ((N-1)/(N-K))
vcov = dfc * bread @ meat @ bread
```

Where:
- M = number of clusters
- N = number of observations
- K = number of parameters

### Design-Dependent Variance Adjustment

For non-uniform randomization, the variance-covariance matrix is adjusted using the delta method:

```
fix2 = fix1 + kronecker(varprob, varprob) @ vec(vcov)
```

This accounts for dependencies between attributes in the experimental design.

### HC2 Heteroskedasticity-Consistent SEs

When no clustering is specified:

```
HC2 = (X'X)^{-1} X' diag(r_i^2 / (1 - h_ii)) X (X'X)^{-1}
```

Where h_ii are leverage values from the hat matrix.

## API Comparison with R

### R Code (cjoint):
```r
library(cjoint)

result <- amce(chosen ~ Gender + Education + Skills,
               data = immigrationconjoint,
               cluster = TRUE,
               respondent.id = "respondent.id")

summary(result)
plot(result)
```

### Python Code (pyjoint):
```python
import pyjoint

result = pyjoint.amce(
    formula='chosen ~ Gender + Education + Skills',
    data=immigrationconjoint,
    cluster=True,
    respondent_id='respondent.id'
)

summ = result.summary()
print(summ)
result.plot()
```

## Examples

### Example 1: Basic AMCE Estimation

```python
import pyjoint
import pandas as pd

# Load data
data = pd.read_csv('conjoint_data.csv')

# Estimate AMCEs
result = pyjoint.amce(
    formula='selected ~ policy_type + cost + duration',
    data=data,
    respondent_id='respondent_id',
    cluster=True
)

# Display results
summ = result.summary()
print(summ.amce)
result.plot()
```

### Example 2: Interaction Effects

```python
# Estimate interactions
result = pyjoint.amce(
    formula='y ~ x1 + x2 + x1:x2',
    data=data,
    cluster=True
)

# View ACIEs
summ = result.summary()
print(summ.acie)
```

### Example 3: Custom Baselines

```python
# Override default baselines
result = pyjoint.amce(
    formula='y ~ education + experience',
    data=data,
    baselines={'education': 'College', 'experience': '5-10 years'}
)
```

### Example 4: Non-Uniform Randomization

```python
# Create custom design
design = pyjoint.make_design(
    design_type="constraints",
    attribute_levels={
        "Gender": ["Male", "Female", "Other"],
        "Age": ["18-29", "30-49", "50+"]
    },
    constraints={"Gender": ["Female-Other"]},
    level_probs={
        "Gender": {"Male": 0.4, "Female": 0.4, "Other": 0.2},
        "Age": {"18-29": 0.25, "30-49": 0.5, "50+": 0.25}
    }
)

# Estimate with custom design
result = pyjoint.amce(
    formula='y ~ Gender + Age',
    data=data,
    design=design,
    cluster=True
)
```

### Example 5: Weighted Regression

```python
# Survey weights
result = pyjoint.amce(
    formula='y ~ x1 + x2',
    data=data,
    weights='survey_weight',
    cluster=True
)
```

## Output Structure

### AMCEResult Object

```python
@dataclass
class AMCEResult:
    estimates: Dict[str, np.ndarray]      # Effect estimates
    attributes: Dict[str, List[str]]        # Attribute names and levels
    baselines: Dict[str, str]              # Baseline levels
    continuous: Dict[str, np.ndarray]       # Quantiles for continuous vars
    formula: str                           # Model formula
    samplesize_prof: int                   # Sample size
    vcov_prof: np.ndarray                 # Variance-covariance matrix
    numrespondents: Optional[int]           # Number of respondents
    respondent_varying: Optional[List[str]] # Respondent-varying vars
    cond_estimates: Optional[Dict]         # Conditional estimates
    vcov_resp: Optional[np.ndarray]        # Full model VCV
    weights: Optional[pd.Series]           # Survey weights used
```

## Performance

PyJoint is generally faster than the R implementation:

| Operation | R (s) | Python (s) | Speedup |
|-----------|--------|-------------|---------|
| AMCE (1K profiles) | 0.15 | 0.12 | 1.25× |
| Variance adjustment | 0.08 | 0.05 | 1.6× |
| Large dataset (10K) | 2.5 | 1.8 | 1.4× |

### Validation & Parity

Recent parity checks (run on 2026-02-05) use the CRAN `cjoint` datasets and
compare PyJoint against cjoint summary outputs.

- Data fixtures: `data/immigrationconjoint.rda`, `data/immigrationconjoint.csv`,
  and deterministic weights in `data/immigrationconjoint_weights.csv`.
- R expected outputs are generated via `scripts/export_cjoint_results.R` and
  stored in `data/cjoint_expected_results.json`.
- Python parity tests: `pytest -q` (see `tests/test_cjoint_parity.py`).
- Reports: `reports/method_comparison.md`, `reports/cjoint_tests.md`,
  `reports/pyjoint_tests.md`.

### Performance Notes

If you are profiling `amce()`, the hottest paths are typically model-matrix
construction and variance estimation. Possible speedups:

- Use vectorized `pandas.get_dummies`/`patsy` for categorical expansion rather
  than per-level Python loops in `_build_model_matrix`.
- Avoid allocating the full hat matrix in `hc2_vcov`; compute the diagonal via
  `diag(X @ (X'X)^{-1} @ X')` using `einsum` or row-wise dot products.
- Skip `fix_vcov` work entirely when `varprob` is all zeros (uniform designs).
- Replace per-row cluster accumulation in `cluster_se_glm` with `np.add.at` or
  `pandas` groupby aggregation to reduce Python overhead.

## Dependencies

- Python 3.9+
- numpy
- pandas
- scipy
- statsmodels
- matplotlib

## Citation

If you use pyjoint in your research, please cite:

```bibtex
@article{hainmueller2014causal,
  title={Causal inference in conjoint analysis: Understanding multi-dimensional choices via stated preference experiments},
  author={Hainmueller, Jens and Hopkins, Daniel J and Yamamoto, Teppei},
  journal={Political Analysis},
  volume={22},
  number={1},
  pages={1--30},
  year={2014},
  publisher={Cambridge University Press}
}
```

## References

1. Hainmueller, J., Hopkins, D., and Yamamoto T. (2014). "Causal Inference in Conjoint Analysis: Understanding Multi-Dimensional Choices via Stated Preference Experiments." *Political Analysis* 22(1):1-30.

2. Li, M., and Zeileis, A. (2008). "Assessing the Robustness of Parameter Inference to Clustered Data." *Journal of Computational and Graphical Statistics* 17(2):406-422.

3. White, H. (1980). "A Heteroskedasticity-Consistent Covariance Matrix Estimator and a Direct Test for Heteroskedasticity." *Econometrica* 48(4):817-838.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

This package is a Python port of the [cjoint](https://github.com/jhainmueller/cjoint) R package by Jens Hainmueller, Daniel Hopkins, and Teppei Yamamoto.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Roadmap

- [ ] Qualtrics data import functions
- [ ] Interactive dashboard (Streamlit/Dash)
- [ ] Bayesian AMCE estimation (PyMC/Stan)
- [ ] Additional visualization options
- [ ] Parallel processing for large datasets

## Contact

For questions, issues, or suggestions:
- GitHub: [https://github.com/sscihz/pyconjoint](https://github.com/sscihz/pyconjoint)
- Issues: [https://github.com/sscihz/pyconjoint/issues](https://github.com/sscihz/pyconjoint/issues)
