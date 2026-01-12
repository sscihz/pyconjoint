# cjoint R Package Architecture Review

## Overview

The **cjoint** package is an R implementation for estimating Average Marginal Component Effects (AMCEs) and Average Component Interaction Effects (ACIEs) from conjoint survey experiments. It follows the methodology from Hainmueller, Hopkins, and Yamamoto (2014).

---

## Package Structure

```
cjoint-master/
├── DESCRIPTION           # Package metadata
├── NAMESPACE            # Exported functions
├── MD5                 # File checksums
├── R/                  # Source code directory
│   ├── cjoint.R                    # Main implementation (2000+ lines)
│   ├── amce-documentation.R        # Function documentation
│   ├── view_amce.R                # Shiny dashboard
│   ├── onAttach.R                 # Package initialization
│   └── test_data/                 # Test datasets
├── data/                # Example datasets (.rda files)
├── man/                 # Documentation files (.Rd files)
├── demo/                # Demo scripts
├── inst/                # Additional resources
│   ├── CandidateConjointQualtrics.csv
│   └── CITATION
└── tests/               # Unit tests
    └── testthat/
        ├── test-main.r
        └── test-plot.R
```

---

## Core Components

### 1. Main Estimation Function (`amce`)

**Location:** `cjoint.R` (lines ~40-1000)

**Purpose:** Estimates AMCEs and ACIEs from conjoint experiment data

**Key Parameters:**
- `formula`: Formula specifying outcome variable and attributes
- `data`: Dataframe with experiment results
- `design`: Either "uniform" or a `conjointDesign` object
- `respondent.varying`: Variables that vary by respondent
- `respondent.id`: Cluster variable for standard errors
- `cluster`: Whether to cluster standard errors
- `weights`: Survey weights column
- `na.ignore`: Handle missing data
- `baselines`: Custom baseline levels
- `subset`: Logical vector for subsetting

**Algorithm Flow:**

1. **Formula Parsing & Cleaning**
   - Parse R formula to extract variables
   - Clean variable names (remove spaces, special characters)
   - Add missing base terms for interactions
   - Separate profile-varying vs respondent-varying variables

2. **Data Validation**
   - Check all variables exist in data
   - Verify factor types for non-respondent variables
   - Check for missing values
   - Validate baseline specifications
   - Check outcome is numeric/integer

3. **Design Matrix Handling**
   - If "uniform": Create uniform probability array
   - If `conjointDesign`: Validate design object
   - Compute dependencies between attributes

4. **Model Estimation**
   - Build design matrix with dependency interactions
   - Run OLS (or weighted OLS using `survey` package)
   - Compute variance-covariance matrix:
     - Clustered SEs if `cluster=TRUE`
     - Robust SEs (HC2) if no clustering
     - Survey package SEs if weights provided

5. **Effect Extraction**
   - Loop over each profile-varying effect
   - Extract coefficient estimates from OLS
   - Adjust for design dependencies using `fix.vcov()` function
   - Weight coefficients by conditional probabilities
   - Compute standard errors with adjusted variance

6. **Conditional Estimation** (if respondent-varying)
   - Separate full model into profile-only and full formulas
   - Extract conditional effects for respondent interactions
   - Adjust variance-covariance matrices

**Key Internal Functions:**

- `clean.names()`: Remove punctuation/spaces from variable names
- `cluster_se_glm()`: Compute clustered standard errors
- `fix.vcov()`: Adjust variance-covariance for design dependencies
- `compute_dependencies()`: Identify dependent attribute relationships

---

### 2. Design Matrix Creation (`makeDesign`)

**Location:** `cjoint.R` (lines ~1600-1750)

**Purpose:** Create conjoint design objects specifying attribute randomization probabilities

**Input Types:**

1. **Type "file"**: Read from Conjoint SDT output file
   - Parse attribute definitions
   - Parse level weights
   - Parse constraints/restrictions

2. **Type "array"**: Accept pre-computed probability array
   - Validate array sums to 1
   - Compute dependencies

3. **Type "constraints"**: Build from attribute levels and constraints
   - Initialize uniform probabilities
   - Apply constraints (set to 0)
   - Renormalize probabilities
   - If level.probs provided, apply weighted marginal randomization

**Output:** `conjointDesign` object containing:
- `$J`: Multidimensional array of profile probabilities
- `$dependence`: List of attribute dependencies

**Dependency Logic:**
- Two attributes are dependent if their joint distribution ≠ product of marginals
- Computed by comparing conditional probabilities across levels
- Used to adjust variance estimates

---

### 3. Summary and Visualization Functions

#### `summary.amce()`
**Location:** `cjoint.R` (lines ~1200-1600)

**Purpose:** Format AMCE results as readable tables

**Key Features:**
- Separate AMCE (main effects) and ACIE (interactions) tables
- Report estimates, standard errors, z-scores, p-values
- Add significance stars (***, **, *)
- Include baseline levels
- Support conditional estimates for respondent-varying effects
- Customizable covariate values for conditional effects

**Output Structure:**
```r
summary_result$amce           # Main effects table
summary_result$acie           # Interaction effects table
summary_result$baselines_amce # Main effect baselines
summary_result$baselines_acie # Interaction baselines
summary_result$table_values_*  # Keys for conditional tables
summary_result$samplesize_*    # Sample sizes
summary_result$respondents     # Number of respondents
```

#### `plot.amce()`
**Location:** `cjoint.R` (lines ~1750-2200)

**Purpose:** Generate ggplot2 coefficient plots

**Key Parameters:**
- `plot.display`: "all", "unconditional", or "interaction"
- `facet.names`: Variables to facet by
- `facet.levels`: Custom facet level specifications
- `ci`: Confidence interval level (default 0.95)
- `colors`: Custom color palette
- `text.size`, `font.family`: Text styling
- `plot.theme`: Custom ggplot2 theme

**Visualization Logic:**
1. Extract estimates and standard errors
2. Calculate confidence intervals
3. Handle baseline levels (display as reference)
4. Support faceting by respondent-varying or interaction variables
5. Apply user-customizable labels and colors
6. Use ggplot2 to create horizontal coefficient plots

---

### 4. Data Import Functions

#### `read.qualtrics()`
**Location:** `cjoint.R` (lines ~2400-2800)

**Purpose:** Import conjoint data from Qualtrics CSV exports

**Input Format:**
- Column names following pattern: `F-Task-Profile-Level` or `F-Task-Level-Attribute`
- Response columns for each task
- Optional respondent ID and covariate columns

**Processing Steps:**
1. Detect format (old vs new Qualtrics)
2. Parse attribute names from column patterns
3. Parse level names
4. Validate responses/ranks
5. Reshape from wide to long format (2-step reshape)
6. Create `selected` indicator variables
7. Return tidy dataframe with columns:
   - `respondent`: Respondent ID
   - `task`: Task number
   - `profile`: Profile number
   - `selected`: Binary outcome
   - Attribute columns as factors

#### `read.with.qualtRics()`
**Location:** `cjoint.R` (lines ~2800-end)

**Purpose:** Import from `qualtRics` package output (pre-parsed Qualtrics data)

**Logic:** Same as `read.qualtrics()` but skips initial parsing steps

---

### 5. Interactive Visualization (`view()`)

**Location:** `view_amce.R`

**Purpose:** Launch Shiny dashboard for interactive AMCE analysis

**Architecture:**

**UI Components:**
- Data/design selector
- Respondent ID and subsetting controls
- Attribute and interaction selectors
- Baseline adjustment controls
- Clustering and weighting options
- Interactive data table
- Results tabs:
  - Summary table
  - Plot (all estimates)
  - Plot (unconditional)
  - Plot (interaction)

**Server Logic:**
- Reactive UI updates based on selected data/design
- Dynamic baseline selector generation
- On-demand AMCE computation
- Interactive plot customization:
  - Text size adjustments
  - Confidence interval sliders
  - Facet selection
  - Font family for non-Latin characters
- Download functionality (PDF reports, CSV summaries)

**Global State Management:**
- `PKG.ENV`: Environment object storing:
  - Available data and design options
  - Current selections
  - Last computed results
  - Plot settings
  - UI element IDs

---

## Key Data Structures

### 1. `amce` Class Object

```r
output$estimates           # List of AMCE/ACIE matrices
output$attributes          # Attribute names and levels
output$baselines           # Baseline levels per attribute
output$continuous          # Quantiles for continuous attributes
output$vcov.prof          # Adjusted variance-covariance (profile)
output$vcov.resp          # Adjusted variance-covariance (full)
output$formula            # Formula used
output$cond.formula       # Formula for conditional effects
output$cond.estimates     # Conditional estimates (if applicable)
output$samplesize_prof    # Sample size (profile model)
output$samplesize_full    # Sample size (full model)
output$numrespondents      # Number of respondents
output$respondent.varying # Respondent-varying variable names
output$weights            # Weights used
output$user.names         # Original user-provided names
output$user.levels        # Original level names
output$data              # Original data
```

### 2. `conjointDesign` Object

```r
design$J                 # Multidimensional array of probabilities
design$depend             # List of dependencies
```

**Example Structure:**
For attributes Gender (2 levels) and Education (3 levels):
```r
design$J <- array(c(0.17, 0.17, 0.16, 0.17, 0.17, 0.16),
                  dim = c(2, 3),
                  dimnames = list(Gender = c("male", "female"),
                                 Education = c("HS", "College", "Grad")))
```

---

## Statistical Methodology

### 1. AMCE Estimation

**Formula:**
```
AMCE_jk = E[Y|X_j=k, X_-j=baseline] - E[Y|X_j=baseline_j, X_-j=baseline]
```

Where:
- `Y` is the outcome
- `X_j` is attribute j
- `k` is a non-baseline level
- `baseline_j` is the reference level of attribute j
- `X_-j` are other attributes at baseline

**Implementation:**
- Estimate via OLS regression of Y on attribute dummy variables
- Coefficient of level k directly estimates AMCE_jk
- Adjust for non-uniform randomization using design matrix

### 2. Variance Estimation

**Without Clustering:**
- Use robust (HC2) standard errors via `sandwich` package

**With Clustering:**
- Use cluster-robust standard errors
- Adjust for within-respondent correlation

**With Design Dependencies:**
- Modify variance-covariance matrix using `fix.vcov()`:
  - Add covariance terms for dependent attributes
  - Weight by conditional probabilities from design matrix
  - Ensures proper uncertainty estimation

### 3. ACIE Estimation

**Formula:**
```
ACIE_{jk,lm} = AMCE_{jk|m} - AMCE_{jk|baseline_m}
```

Where `m` and `l` are levels of a second attribute

**Implementation:**
- Estimate interaction terms in OLS
- Extract interaction coefficients
- Adjust for baseline support

### 4. Conditional AMCEs

**Purpose:** Estimate AMCEs at specific values of respondent characteristics

**Formula:**
```
Conditional AMCE = β_main + β_interaction * respondent_level
```

**Implementation:**
- Run full model with interaction terms
- Compute conditional effects using `get.conditional.effects()`
- Adjust standard errors for interaction variance

---

## Dependencies

### Required R Packages

```
ggplot2     # Visualization
lmtest       # Linear model testing
Matrix       # Sparse matrix operations
sandwich     # Robust standard errors
survey       # Weighted regression
stats        # Core statistics
utils        # Utilities
```

### Optional Dependencies (for `view()`)
```
shiny        # Interactive dashboard
shinyjs      # JavaScript integration in Shiny
DT           # Interactive tables
```

---

## Testing Strategy

### Test Coverage (`tests/testthat/test-main.r`)

**Test Categories:**

1. **Basic Functionality**
   - Output class verification (`expect_is(mod, "amce")`)
   - Default parameters

2. **Clustering**
   - Clustered vs non-clustered estimation
   - Warning when `respondent.id` is NULL

3. **Weights**
   - Weighted estimation
   - Uniform weights warning

4. **Interactions**
   - Missing base term auto-addition
   - ACIE computation

5. **Data Validation**
   - Duplicate variable names
   - Missing variables
   - Non-factor attributes (auto-convert warning)
   - Missing data handling
   - Outcome variable type

6. **Baseline Handling**
   - Invalid baseline levels
   - Custom baseline specification

7. **Design Object**
   - Attribute missing from design
   - Level missing from design
   - Design vs data mismatch

8. **Respondent Varying**
   - Not in formula error
   - Conditional estimation

9. **Subsetting**
   - Invalid subset type
   - Subset length mismatch

10. **Data Import**
    - Qualtrics format validation
    - Response/rank column counts
    - Attribute level uniqueness

---

## Architecture Patterns

### 1. S3 Object-Oriented System

The package uses R's S3 class system:
- `amce`: Main result class with `summary.amce()` and `plot.amce()` methods
- `conjointDesign`: Design matrix class

### 2. Functional Programming

- Pure functions for estimation, visualization, data import
- No side effects (except `view()` which uses global state)
- Explicit parameter passing

### 3. Validation-First Design

- Extensive input validation at function entry
- Clear error messages with context
- Warnings for non-critical issues

### 4. Formula-Based Interface

- Uses R's formula syntax for model specification
- Automatic interaction handling (`:` and `*`)
- Familiar to R users

### 5. Lazy Evaluation

- Conditional estimation only computed if needed
- Plot data generated on demand

---

## Performance Considerations

### 1. Computational Complexity

- **Estimation**: O(n × p²) where n = observations, p = parameters
- **Variance adjustment**: O(p³) for matrix operations
- **Visualization**: O(k) where k = number of levels

### 2. Memory Usage

- Design matrices stored as dense arrays
- Large experiments (many attributes/levels) may require significant RAM
- Uses sparse matrices for variance adjustment (`Matrix` package)

### 3. Optimization Strategies

- Vectorized operations where possible
- Pre-computed design probabilities
- Efficient formula parsing

---

## Extension Points for Python Port

### 1. Core Estimation Engine

**Python Equivalent Libraries:**
- `statsmodels` for OLS and robust SEs
- `scipy.sparse` for sparse matrices
- `numpy` for array operations

**Key Functions to Port:**
- `amce()`: Main estimation
- `cluster_se_glm()`: Clustered SEs
- `fix.vcov()`: Variance adjustment
- `compute_dependencies()`: Dependency detection

### 2. Data Structures

**Python Classes:**
```python
class AMCE:
    estimates: Dict[str, np.ndarray]
    attributes: Dict[str, List[str]]
    baselines: Dict[str, str]
    vcov_prof: np.ndarray
    vcov_resp: np.ndarray
    formula: str
    # ... other fields

class ConjointDesign:
    J: np.ndarray
    dependencies: Dict[str, List[str]]
```

### 3. Visualization

**Python Equivalent Libraries:**
- `matplotlib` + `seaborn` or `plotnine` (ggplot2 clone)
- Interactive: `streamlit` or `dash` (like Shiny)

### 4. Data Import

**Python Implementation:**
- Use `pandas` for CSV reading
- Reshape using `pandas.melt()` or `pd.wide_to_long()`
- Similar column parsing logic

### 5. API Design Recommendations

**Function Signature Style:**
```python
def amce(formula: str,
         data: pd.DataFrame,
         design: Union[str, ConjointDesign] = "uniform",
         respondent_varying: Optional[List[str]] = None,
         respondent_id: Optional[str] = None,
         cluster: bool = True,
         weights: Optional[str] = None,
         na_ignore: bool = False,
         baselines: Optional[Dict[str, str]] = None,
         subset: Optional[np.ndarray] = None) -> AMCE:
    ...
```

---

## Known Limitations

1. **Memory**: Large design arrays can be memory-intensive
2. **Speed**: Variance adjustment matrix operations can be slow
3. **Factors**: All profile-varying attributes must be factors
4. **Binary Outcome**: Assumes 0-1 outcome (though numeric works)
5. **Design Restrictions**: Only handles profile-level constraints

---

## References

Hainmueller, J., Hopkins, D., and Yamamoto T. (2014) "Causal Inference in Conjoint Analysis: Understanding Multi-Dimensional Choices via Stated Preference Experiments." *Political Analysis* 22(1):1-30.

---

## Summary

The cjoint package is well-structured with:
- ✅ Clear separation of concerns (estimation, visualization, data import)
- ✅ Extensive input validation
- ✅ Comprehensive testing
- ✅ Documentation-rich code
- ✅ Interactive exploration tools
- ✅ Support for complex experimental designs

**Key Challenges for Python Port:**
1. Formula parsing (R's formula system vs Python)
2. S3 method dispatch vs Python OOP
3. Statistical library differences (survey package equivalents)
4. Visualization library choice (ggplot2 style vs matplotlib)
5. Interactive dashboard (Shiny vs Streamlit/Dash)

**Recommended Approach:**
1. Start with core `amce()` function
2. Implement basic AMCE estimation
3. Add variance adjustment logic
4. Implement visualization
5. Add interactive features later
6. Port data import functions
