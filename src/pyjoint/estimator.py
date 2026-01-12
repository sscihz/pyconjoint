"""
Main AMCE/ACIE estimator for pyjoint.

This module replicates R's amce function, which estimates Average Marginal
Component Effects (AMCEs) and Average Component Interaction Effects (ACIEs)
from conjoint survey experiments.
"""

import numpy as np
import pandas as pd
import warnings
from typing import List, Dict, Optional, Union
from dataclasses import dataclass

from .naming import (
    clean_names, clean_names_vectorized, split_interaction_term,
    create_coef_name, validate_unique_names, validate_unique_levels
)
from .design import ConjointDesign, compute_dependencies
from .vcov import cluster_se_glm, fix_vcov, hc2_vcov


@dataclass
class AMCEResult:
    """
    Result object from AMCE estimation.
    
    Attributes
    ----------
    estimates : Dict[str, np.ndarray]
        Dictionary mapping effect names to 2xN arrays (estimates, SEs)
    attributes : Dict[str, List[str]]
        Dictionary mapping attribute names to their levels
    baselines : Dict[str, str]
        Baseline levels for each factor attribute
    continuous : Dict[str, np.ndarray]
        Quantiles for continuous variables
    formula : str
        The formula used for estimation
    samplesize_prof : int
        Number of profiles in the dataset
    vcov_prof : np.ndarray
        Variance-covariance matrix for profile effects
    numrespondents : Optional[int]
        Number of respondents (if respondent.id provided)
    respondent_varying : Optional[List[str]]
        List of respondent-varying variable names
    cond_estimates : Optional[Dict[str, np.ndarray]]
        Conditional effect estimates
    vcov_resp : Optional[np.ndarray]
        VCV matrix for respondent effects
    samplesize_full : Optional[int]
        Sample size with respondent effects
    cond_formula : Optional[str]
        Formula for conditional effects
    weights : Optional[pd.Series]
        Survey weights
    user_names : Dict[str, str]
        Original user-supplied variable names
    user_levels : Dict[str, str]
        Original user-supplied level names
    data : pd.DataFrame
        The original data (after cleaning)
    """
    estimates: Dict[str, np.ndarray]
    attributes: Dict[str, List[str]]
    baselines: Dict[str, str]
    continuous: Dict[str, np.ndarray]
    formula: str
    samplesize_prof: int
    vcov_prof: np.ndarray
    numrespondents: Optional[int] = None
    respondent_varying: Optional[List[str]] = None
    cond_estimates: Optional[Dict[str, np.ndarray]] = None
    vcov_resp: Optional[np.ndarray] = None
    samplesize_full: Optional[int] = None
    cond_formula: Optional[str] = None
    weights: Optional[pd.Series] = None
    user_names: Optional[Dict[str, str]] = None
    user_levels: Optional[Dict[str, str]] = None
    data: Optional[pd.DataFrame] = None


def amce(
    formula: str,
    data: pd.DataFrame,
    design: Union[str, ConjointDesign] = "uniform",
    respondent_varying: Optional[List[str]] = None,
    subset: Optional[np.ndarray] = None,
    respondent_id: Optional[str] = None,
    cluster: bool = True,
    na_ignore: bool = False,
    weights: Optional[str] = None,
    baselines: Optional[Dict[str, str]] = None
) -> AMCEResult:
    """
    Estimate AMCEs and ACIEs from conjoint experiment data.
    
    This is the main estimation function for pyjoint, replicating R's amce().
    
    Parameters
    ----------
    formula : str
        Model formula in R-style format: "Y ~ X1 + X2 + X1:X2"
    data : pd.DataFrame
        Dataset containing outcome, attributes, and covariates
    design : Union[str, ConjointDesign], default="uniform"
        Either "uniform" or a ConjointDesign object from make_design()
    respondent_varying : List[str], optional
        List of respondent-level variable names to interact with
    subset : np.ndarray, optional
        Logical vector for subsetting data
    respondent_id : str, optional
        Column name for respondent identifier
    cluster : bool, default=True
        Whether to cluster standard errors on respondent_id
    na_ignore : bool, default=False
        Whether to ignore missing values
    weights : str, optional
        Column name for survey weights
    baselines : Dict[str, str], optional
        Dictionary of baseline levels to override defaults
        
    Returns
    -------
    AMCEResult
        Object containing estimates and metadata
        
    Examples
    --------
    >>> import pandas as pd
    >>> import numpy as np
    >>> # Create simple conjoint data
    >>> data = pd.DataFrame({
    ...     'chosen': np.random.randint(0, 2, 1000),
    ...     'Gender': np.random.choice(['Male', 'Female'], 1000),
    ...     'Education': np.random.choice(['HS', 'College'], 1000),
    ...     'respondent_id': np.repeat(np.arange(500), 2)
    ... })
    >>> result = amce('chosen ~ Gender + Education', data, 
    ...              respondent_id='respondent_id', cluster=True)
    >>> print(result.estimates['Gender'])
    """
    # Parse formula
    formula_parts = _parse_formula(formula)
    y_var = formula_parts['y']
    x_vars = formula_parts['x']
    interactions = formula_parts['interactions']
    
    # Clean variable names
    cleaned_data = data.copy()
    cleaned_data.columns = clean_names_vectorized(list(cleaned_data.columns))
    y_var_clean = clean_names(y_var)
    x_vars_clean = clean_names_vectorized(x_vars)
    interactions_clean = clean_names_vectorized(interactions)
    if respondent_varying:
        respondent_varying_clean = clean_names_vectorized(respondent_varying)
    else:
        respondent_varying_clean = []
    
    if weights:
        weights_clean = clean_names(weights)
    else:
        weights_clean = None
    
    if respondent_id:
        respondent_id_clean = clean_names(respondent_id)
    else:
        respondent_id_clean = None
    
    # Validate unique names
    all_vars = [y_var_clean] + x_vars_clean
    validate_unique_names(all_vars)
    
    # Separate profile and respondent variables
    profile_vars = [v for v in x_vars_clean if v not in respondent_varying_clean]
    
    # Apply baselines
    if baselines:
        cleaned_baselines = {clean_names(k): clean_names(v) for k, v in baselines.items()}
        for var, baseline in cleaned_baselines.items():
            if var in cleaned_data.columns:
                # Convert to categorical if needed
                if cleaned_data[var].dtype == 'object':
                    cleaned_data[var] = pd.Categorical(cleaned_data[var])
                # Set baseline
                if hasattr(cleaned_data[var], 'categories'):
                    cleaned_data[var] = cleaned_data[var].cat.reorder_categories(
                        list(cleaned_data[var].cat.categories),
                        ordered=True
                    )
    
    # Ensure profile variables are factors (categorical)
    for var in profile_vars:
        if cleaned_data[var].dtype != 'category':
            cleaned_data[var] = pd.Categorical(cleaned_data[var])
            warnings.warn(f"Warning: {var} changed to factor")
    
    # Check for missing values
    if not na_ignore:
        vars_to_check = [y_var_clean] + x_vars_clean
        for var in vars_to_check:
            if var in cleaned_data.columns and cleaned_data[var].isna().any():
                raise ValueError(f"Error: {var} has missing values in 'data'")
    
    # Subset data
    if subset is not None:
        if len(subset) == len(cleaned_data):
            cleaned_data = cleaned_data[subset]
        else:
            warnings.warn("Warning: invalid argument to 'subset'")
    
    # Handle design
    if isinstance(design, str) and design == "uniform":
        # Create uniform design array
        design_obj = _create_uniform_design(cleaned_data, profile_vars)
    elif isinstance(design, ConjointDesign):
        design_obj = design
    else:
        raise ValueError("Design object must be 'uniform' or ConjointDesign object")
    
    # Build model matrix
    X, y, coef_names = _build_model_matrix(
        cleaned_data, y_var_clean, x_vars_clean, interactions_clean
    )
    
    # Fit model
    model_results = _fit_model(
        X, y, weights_clean, cleaned_data, respondent_id_clean
    )
    
    # Compute variance-covariance matrix
    if weights_clean:
        vcov_mat = model_results['vcov']
    elif respondent_id_clean and cluster:
        vcov_mat = cluster_se_glm(model_results['model'], 
                                   cleaned_data[respondent_id_clean].values)
    else:
        vcov_mat = hc2_vcov(model_results['model'])
    
    # Extract AMCE/ACIE estimates
    estimates, varprob_mat = _extract_effects(
        cleaned_data, profile_vars, interactions_clean,
        design_obj, model_results, x_vars_clean
    )
    
    # Adjust variance-covariance matrix
    vcov_prof = fix_vcov(varprob_mat, vcov_mat)
    
    # Extract baseline and continuous variable info
    baselines_dict = {}
    continuous_dict = {}
    for var in profile_vars:
        if cleaned_data[var].dtype == 'category':
            baselines_dict[var] = str(cleaned_data[var].cat.categories[0])
        elif np.issubdtype(cleaned_data[var].dtype, np.number):
            continuous_dict[var] = np.quantile(
                cleaned_data[var].values, [0.25, 0.5, 0.75]
            )
    
    # Get sample sizes
    samplesize_prof = len(y)
    numrespondents = None
    if respondent_id_clean:
        numrespondents = len(np.unique(cleaned_data[respondent_id_clean].values))
    
    return AMCEResult(
        estimates=estimates,
        attributes={var: list(cleaned_data[var].cat.categories) 
                    for var in profile_vars 
                    if cleaned_data[var].dtype == 'category'},
        baselines=baselines_dict,
        continuous=continuous_dict,
        formula=formula,
        samplesize_prof=samplesize_prof,
        vcov_prof=vcov_prof,
        numrespondents=numrespondents,
        respondent_varying=respondent_varying_clean if respondent_varying_clean else None,
        data=cleaned_data
    )


def _parse_formula(formula: str) -> Dict[str, List[str]]:
    """Parse R-style formula string."""
    # Simple formula parser: "Y ~ X1 + X2 + X1:X2"
    parts = formula.split('~')
    if len(parts) != 2:
        raise ValueError(f"Invalid formula: {formula}")
    
    y_var = parts[0].strip()
    rhs = parts[1].strip()
    
    # Split by + to get terms
    terms = [t.strip() for t in rhs.split('+') if t.strip()]
    
    # Separate main effects and interactions
    x_vars = []
    interactions = []
    for term in terms:
        if ':' in term or '*' in term:
            interactions.append(term)
        else:
            x_vars.append(term)
    
    return {
        'y': y_var,
        'x': x_vars,
        'interactions': interactions
    }


def _create_uniform_design(data: pd.DataFrame, profile_vars: List[str]) -> ConjointDesign:
    """Create uniform design array from data."""
    dimensions = []
    dimnames = {}
    
    for var in profile_vars:
        if data[var].dtype == 'category':
            n_levels = len(data[var].cat.categories)
            levels = list(data[var].cat.categories)
        else:
            # For continuous, create bins
            n_levels = 4
            levels = [f'bin{i}' for i in range(n_levels)]
        
        dimensions.append(n_levels)
        dimnames[var] = levels
    
    # Create uniform probability array
    total_cells = np.prod(dimensions)
    J = np.ones(dimensions) / total_cells
    
    # Compute dependencies
    dependence = compute_dependencies(J)
    
    return ConjointDesign(J=J, dependence=dependence)


def _build_model_matrix(
    data: pd.DataFrame,
    y_var: str,
    x_vars: List[str],
    interactions: List[str]
) -> tuple:
    """Build model matrix with dummy variables for factors."""
    y = data[y_var].values
    
    # Build design matrix column by column
    X_list = [np.ones(len(data))]  # Intercept
    coef_names = ['Intercept']
    
    # Add main effects (excluding baseline level)
    for var in x_vars:
        if data[var].dtype == 'category':
            categories = list(data[var].cat.categories)
            for level in categories[1:]:  # Skip first (baseline)
                dummy = (data[var] == level).astype(float)
                X_list.append(dummy.values)
                coef_names.append(create_coef_name(var, str(level)))
        else:
            X_list.append(data[var].values)
            coef_names.append(var)
    
    # Add interaction terms
    for inter in interactions:
        components = split_interaction_term(inter)
        if len(components) == 2:
            var1, var2 = components
            if data[var1].dtype == 'category' and data[var2].dtype == 'category':
                # Both categorical: interaction of non-baseline levels
                cats1 = list(data[var1].cat.categories)[1:]
                cats2 = list(data[var2].cat.categories)[1:]
                for l1 in cats1:
                    for l2 in cats2:
                        inter_dummy = ((data[var1] == l1) & (data[var2] == l2)).astype(float)
                        X_list.append(inter_dummy.values)
                        coef_names.append(f"{create_coef_name(var1, l1)}:{create_coef_name(var2, l2)}")
    
    X = np.column_stack(X_list)
    
    return X, y, coef_names


def _fit_model(
    X: np.ndarray,
    y: np.ndarray,
    weights: Optional[str],
    data: pd.DataFrame,
    respondent_id: Optional[str]
) -> Dict:
    """Fit linear model (OLS or weighted)."""
    try:
        import statsmodels.api as sm
    except ImportError:
        raise ImportError("statsmodels is required for model fitting")
    
    if weights is not None:
        # Weighted least squares
        w = data[weights].values
        model = sm.WLS(y, X, weights=w).fit()
    else:
        # OLS
        model = sm.OLS(y, X).fit()
    
    return {
        'model': model,
        'vcov': model.cov_params(),
        'coefficients': model.params,
        'residuals': model.resid
    }


def _extract_effects(
    data: pd.DataFrame,
    profile_vars: List[str],
    interactions: List[str],
    design_obj: ConjointDesign,
    model_results: Dict,
    x_vars: List[str]
) -> tuple:
    """Extract AMCE/ACIE estimates from model results."""
    estimates = {}
    coefficients = model_results['coefficients']
    coef_names = list(coefficients.index)
    
    # Initialize variance probability matrix
    varprob_mat = np.zeros((len(coef_names), len(coef_names)))
    varprob_mat = pd.DataFrame(varprob_mat, index=coef_names, columns=coef_names)
    
    # Extract effects for each variable
    for var in profile_vars:
        if data[var].dtype == 'category':
            categories = list(data[var].cat.categories)
            n_levels = len(categories)
            
            # Create results matrix: 2 rows (est, SE), n_levels cols
            results = np.full((2, n_levels), np.nan)
            row_names = ['AMCE', 'Std. Error']
            col_names = [create_coef_name(var, str(l)) for l in categories]
            
            # Fill estimates
            for i, level in enumerate(categories[1:]):  # Skip baseline
                coef_name = create_coef_name(var, str(level))
                if coef_name in coef_names:
                    results[0, i+1] = coefficients[coef_name]
            
            estimates[var] = pd.DataFrame(results, index=row_names, columns=col_names)
    
    # Extract interaction effects
    for inter in interactions:
        components = split_interaction_term(inter)
        if len(components) == 2:
            var1, var2 = components
            if data[var1].dtype == 'category' and data[var2].dtype == 'category':
                cats1 = list(data[var1].cat.categories)[1:]
                cats2 = list(data[var2].cat.categories)[1:]
                
                n_cells = len(cats1) * len(cats2)
                results = np.full((2, n_cells), np.nan)
                row_names = ['ACIE', 'Std. Error']
                col_names = []
                
                idx = 0
                for l1 in cats1:
                    for l2 in cats2:
                        coef_name = f"{create_coef_name(var1, l1)}:{create_coef_name(var2, l2)}"
                        col_names.append(coef_name)
                        if coef_name in coef_names:
                            results[0, idx] = coefficients[coef_name]
                        idx += 1
                
                estimates[inter] = pd.DataFrame(results, index=row_names, columns=col_names)
    
    return estimates, varprob_mat
