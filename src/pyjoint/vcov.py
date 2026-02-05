"""
Variance-covariance matrix computation for pyjoint.

This module replicates R's cluster_se_glm and fix.vcov functions,
which handle cluster-robust standard errors and variance adjustments
for dependent attributes in conjoint experiments.
"""

import numpy as np
import scipy.sparse as sp
from typing import Optional, Union
import warnings


def cluster_se_glm(model, cluster: np.ndarray) -> np.ndarray:
    """
    Compute cluster-robust variance-covariance matrix for GLM.
    
    This replicates R's cluster_se_glm function with small-sample correction:
    dfc = (M/(M-1)) * ((N-1)/(N-K))
    vcov_clustered = dfc * sandwich(model, meat. = crossprod(uj)/N)
    
    Parameters
    ----------
    model : object
        Fitted model object with residuals and influence functions.
        Must have:
        - model.nobs: number of observations
        - model.rank: rank of model matrix (number of parameters)
        - model.resid_response: residuals
        - model.model_exog: design matrix
    cluster : np.ndarray
        Array of cluster indicators
        
    Returns
    -------
    np.ndarray
        Cluster-robust variance-covariance matrix
        
    Raises
    ------
    ValueError
        If cluster variable has different length than model observations
        
    Examples
    --------
    >>> # After fitting a model with statsmodels
    >>> import statsmodels.api as sm
    >>> X = np.column_stack([np.ones(100), np.random.randn(100)])
    >>> y = X @ np.array([1, 2]) + np.random.randn(100)
    >>> model = sm.OLS(y, X).fit()
    >>> cluster_ids = np.repeat(np.arange(50), 2)
    >>> vcov_clustered = cluster_se_glm(model, cluster_ids)
    """
    # Convert cluster to numpy array if needed
    cluster = np.asarray(cluster)
    
    # Drop unused cluster indicators, if cluster var has unique values
    # (R's droplevels equivalent - handled by numpy unique)
    
    N = int(model.nobs)  # Number of observations
    K = len(model.params)  # Number of fitted parameters (including intercept)
    M = len(np.unique(cluster))  # Number of clusters
    
    if N != len(cluster):
        raise ValueError(
            "check your data: cluster variable has different N than model - "
            "you may have observations with missing data"
        )
    
    # Small-sample correction factor (Li and Zeileis, 2008)
    dfc = (M / (M - 1)) * ((N - 1) / (N - K))
    
    # Compute influence functions (u_i = score_i = x_i * e_i)
    # For OLS, this is: x_i * residual_i
    X = model.model.exog
    residuals = np.asarray(model.resid)
    
    # Compute score for each observation
    u = X * residuals[:, np.newaxis]  # Shape: (N, K)
    
    # Sum scores within clusters
    # Create a mapping from cluster id to index
    unique_clusters = np.unique(cluster)
    cluster_to_idx = {c: i for i, c in enumerate(unique_clusters)}
    
    # Sum u for each cluster
    uj = np.zeros((M, K))
    for i, c in enumerate(cluster):
        cluster_idx = cluster_to_idx[c]
        uj[cluster_idx, :] += u[i, :]
    
    # Compute meat of sandwich estimator: (1/N) * uj' * uj
    meat = (uj.T @ uj) / N
    
    # Get bread of sandwich estimator: X'X inverse
    # For OLS, this is (X'X)^{-1}
    bread = np.linalg.inv(X.T @ X)
    
    # Compute clustered VCV: dfc * bread * meat * bread
    vcov_clustered = dfc * (bread @ meat @ bread)
    
    return vcov_clustered


def fix_vcov(varprob: np.ndarray, vcov: np.ndarray) -> np.ndarray:
    """
    Adjust variance-covariance matrix for dependent attributes.
    
    This replicates R's fix.vcov function which uses the delta method
    to adjust variances when coefficients depend on other coefficients
    through conditional probabilities.
    
    Mathematical derivation:
    For β_adj = β_initial + Σ p_i * β_i where p_i are conditional probs:
    
    Var(β_adj) = Var(β_initial) + Var(Σ p_i β_i) + 2Cov(β_initial, Σ p_i β_i)
    
    Using sparse matrices for efficiency (as in R's Matrix package):
    
    fix1 = varprob @ vcov + (varprob @ vcov).T + vcov
    fix2 = fix1 + kronecker(varprob, varprob) @ vec(vcov)
    
    Parameters
    ----------
    varprob : np.ndarray
        Matrix of probability weights for dependent coefficients.
        Shape: (K, K) where K is number of coefficients
    vcov : np.ndarray
        Original variance-covariance matrix from model.
        Shape: (K, K)
        
    Returns
    -------
    np.ndarray
        Adjusted variance-covariance matrix
        
    Examples
    --------
    >>> K = 5
    >>> varprob = np.zeros((K, K))
    >>> varprob[0, 1] = 0.5  # Coeff 1 depends on coeff 2 with prob 0.5
    >>> vcov = np.eye(K) * 0.1
    >>> vcov_adj = fix_vcov(varprob, vcov)
    """
    # Convert to sparse matrices for efficiency
    varprob_sparse = sp.csr_matrix(varprob)
    vcov_sparse = sp.csr_matrix(vcov)
    
    # Calculate single sum corrections
    # fix1 = varprob @ vcov + (varprob @ vcov).T + vcov
    fix1 = varprob_sparse @ vcov_sparse
    fix1 = fix1 + fix1.T
    fix1 = fix1 + vcov_sparse
    
    # Compute weighted cross terms
    # vec(vcov) = reshape vcov to vector
    vcov_vector = vcov_sparse.reshape(-1, 1)
    
    # kronecker product of varprob with itself
    kron_prod = sp.kron(varprob_sparse, varprob_sparse)
    
    # weighted_covs = kron(varprob, varprob) @ vec(vcov)
    weighted_covs = kron_prod @ vcov_vector
    weighted_covs = weighted_covs.reshape(vcov.shape)
    
    # Add cross terms to single sum corrections
    fix2 = fix1 + weighted_covs
    
    # Convert back to dense matrix
    vcov_adj = np.array(fix2.todense())
    
    return vcov_adj


def compute_weighted_covariance(
    pred_mat: np.ndarray,
    vcov: np.ndarray,
    var_names: list
) -> float:
    """
    Compute variance of a linear combination of coefficients.
    
    For a prediction y = pred_mat @ β, the variance is:
    Var(y) = pred_mat @ vcov @ pred_mat.T
    
    Parameters
    ----------
    pred_mat : np.ndarray
        Prediction matrix (row vector for single prediction).
        Shape: (1, K) or (K,)
    vcov : np.ndarray
        Variance-covariance matrix.
        Shape: (K, K)
    var_names : list
        List of variable names (for checking)
        
    Returns
    -------
    float
        Standard error of the prediction
        
    Examples
    --------
    >>> pred_mat = np.array([[1, 0.5, 0]])
    >>> vcov = np.eye(3) * 0.1
    >>> se = compute_weighted_covariance(pred_mat, vcov, ['intercept', 'x1', 'x2'])
    """
    # Ensure pred_mat is 2D
    if pred_mat.ndim == 1:
        pred_mat = pred_mat.reshape(1, -1)
    
    # Compute variance: pred_mat @ vcov @ pred_mat.T
    variance = pred_mat @ vcov @ pred_mat.T
    se = np.sqrt(variance[0, 0])
    
    return se


def hc2_vcov(model: object) -> np.ndarray:
    """
    Compute HC2 (heteroskedasticity-consistent) standard errors.
    
    This replicates R's vcovHC with type="HC2":
    HC2 = (X'X)^{-1} X' diag(r_i^2 / (1 - h_ii)) X (X'X)^{-1}
    
    where h_ii are leverage values from hat matrix H = X(X'X)^{-1}X'
    
    Parameters
    ----------
    model : object
        Fitted model object with model matrix and residuals
        
    Returns
    -------
    np.ndarray
        HC2 variance-covariance matrix
        
    Examples
    --------
    >>> import statsmodels.api as sm
    >>> X = np.column_stack([np.ones(100), np.random.randn(100)])
    >>> y = X @ np.array([1, 2]) + np.random.randn(100)
    >>> model = sm.OLS(y, X).fit()
    >>> vcov_hc2 = hc2_vcov(model)
    """
    X = np.asarray(model.model.exog)
    residuals = np.asarray(model.resid)
    n = X.shape[0]
    
    # Compute hat matrix: H = X(X'X)^{-1}X'
    XtX_inv = np.linalg.inv(X.T @ X)
    H = X @ XtX_inv @ X.T
    
    # Leverage values (diagonal of H)
    h = np.diag(H)
    
    # Compute weights: r_i^2 / (1 - h_ii)
    weights = residuals**2 / (1 - h)
    
    # Weighted residual matrix: W^{1/2} X
    sqrt_weights = np.sqrt(weights)
    W_sqrt_X = X * sqrt_weights[:, np.newaxis]
    
    # HC2 meat: X' W X
    meat = W_sqrt_X.T @ W_sqrt_X
    
    # HC2 VCV: (X'X)^{-1} meat (X'X)^{-1}
    vcov_hc2 = XtX_inv @ meat @ XtX_inv
    
    return vcov_hc2
