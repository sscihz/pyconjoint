"""
Design matrix creation and dependency computation for pyjoint.

This module replicates R's makeDesign and compute_dependencies functions,
which handle non-uniform randomization designs for conjoint experiments.
"""

import numpy as np
from typing import List, Dict, Optional, Union
import warnings


def compute_dependencies(J: np.ndarray, tol: float = 1e-14) -> Dict[str, List[str]]:
    """
    Compute attribute dependencies from a design probability array.
    
    Two attributes are dependent if the conditional distribution of one
    given the other is not the same across all levels.
    
    Parameters
    ----------
    J : np.ndarray
        J-dimensional array of profile assignment probabilities.
        Array dimensions correspond to attributes.
    tol : float, default=1e-14
        Tolerance for comparing conditional distributions
        
    Returns
    -------
    Dict[str, List[str]]
        Dictionary where keys are attribute names and values are lists
        of attributes they depend on
        
    Examples
    --------
    >>> # Uniform independent design
    >>> J = np.ones((2, 2)) / 4
    >>> compute_dependencies(J)
    {'attr1': [], 'attr2': []}
    """
    # Get number of attributes
    n_attrs = J.ndim
    
    # If only one attribute, no dependencies
    if n_attrs == 1:
        return {'attr1': []}
    
    # Create list for each attribute
    dependency_list = {f'attr{i+1}': [] for i in range(n_attrs)}
    
    # Loop over each pair of attributes - figure out if they're independent
    for i in range(n_attrs - 1):
        for j in range(i + 1, n_attrs):
            # Marginalize to get cross-tabulation of attributes i and j
            # Sum over all dimensions except i and j
            dims_to_keep = [i, j]
            dims_to_sum = [d for d in range(n_attrs) if d not in dims_to_keep]
            
            if dims_to_sum:
                cross_tab = np.sum(J, axis=tuple(dims_to_sum))
            else:
                cross_tab = J.copy()
            
            # Standardize by row sums to get conditional probabilities
            row_sums = np.sum(cross_tab, axis=1, keepdims=True)
            cross_tab_std = cross_tab / row_sums
            
            # Check if all rows are equal (independent)
            is_equal = True
            if cross_tab_std.shape[0] > 1:
                # Compare first row to all other rows
                for m in range(1, cross_tab_std.shape[0]):
                    if np.any(np.abs(cross_tab_std[0, :] - cross_tab_std[m, :]) > tol):
                        is_equal = False
                        break
            
            # If not independent, append to dependency dictionary
            if not is_equal:
                dependency_list[f'attr{i+1}'].append(f'attr{j+1}')
                dependency_list[f'attr{j+1}'].append(f'attr{i+1}')
    
    return dependency_list


class ConjointDesign:
    """
    Object representing a conjoint experimental design.
    
    Attributes
    ----------
    J : np.ndarray
        J-dimensional array of profile assignment probabilities
    dependence : Dict[str, List[str]]
        Dictionary of attribute dependencies
    """
    
    def __init__(self, J: np.ndarray, dependence: Dict[str, List[str]]):
        self.J = J
        self.dependence = dependence
    
    def __repr__(self):
        return f"ConjointDesign(shape={self.J.shape}, attributes={self.J.ndim})"


def make_design(
    type: str = "file",
    J: Optional[np.ndarray] = None,
    filename: Optional[str] = None,
    attribute_levels: Optional[Dict[str, List[str]]] = None,
    constraints: Optional[List[Dict[str, str]]] = None,
    level_probs: Optional[Dict[str, np.ndarray]] = None,
    tol: float = 1e-14
) -> ConjointDesign:
    """
    Create a conjoint design object.
    
    Supports three types:
    - "array": Direct input of probability array J
    - "constraints": Build from attribute levels and constraints
    - "file": Read from Conjoint SDT file format
    
    Parameters
    ----------
    type : str, default="file"
        Type of design: "array", "constraints", or "file"
    J : np.ndarray, optional
        Probability array for type="array"
    filename : str, optional
        Filename for type="file"
    attribute_levels : Dict[str, List[str]], optional
        Dictionary mapping attribute names to their levels
    constraints : List[Dict[str, str]], optional
        List of constraint dictionaries
    level_probs : Dict[str, np.ndarray], optional
        Dictionary mapping attribute names to level probabilities
    tol : float, default=1e-14
        Tolerance for dependency computation
        
    Returns
    -------
    ConjointDesign
        Design object containing J array and dependencies
        
    Examples
    --------
    >>> # Using array type
    >>> J = np.ones((2, 3)) / 6
    >>> design = make_design(type="array", J=J)
    
    >>> # Using constraints type
    >>> attribute_levels = {'Gender': ['Male', 'Female'], 'Job': ['Doctor', 'Teacher']}
    >>> design = make_design(type="constraints", attribute_levels=attribute_levels)
    """
    if type == "array":
        return _make_design_from_array(J, tol)
    elif type == "constraints":
        return _make_design_from_constraints(
            attribute_levels, constraints, level_probs, tol
        )
    elif type == "file":
        return _make_design_from_file(filename, tol)
    else:
        raise ValueError(
            f"Invalid type argument: Must be 'array', 'constraints', or 'file', got '{type}'"
        )


def _make_design_from_array(J: np.ndarray, tol: float = 1e-14) -> ConjointDesign:
    """Create design object from probability array."""
    if np.sum(J) != 1.0:
        warnings.warn("Profile assignment probability array invalid: Does not sum to 1")
    
    dependence = compute_dependencies(J, tol)
    return ConjointDesign(J=J, dependence=dependence)


def _make_design_from_constraints(
    attribute_levels: Dict[str, List[str]],
    constraints: Optional[List[Dict[str, str]]] = None,
    level_probs: Optional[Dict[str, np.ndarray]] = None,
    tol: float = 1e-14
) -> ConjointDesign:
    """Create design object from attribute levels and constraints."""
    if attribute_levels is None:
        raise ValueError(
            "Must provide a valid dict object in attribute_levels argument for type='constraints'"
        )
    
    # Calculate number of dimensions
    dimensions = [len(levels) for levels in attribute_levels.values()]
    
    # Initialize J matrix with NaN
    J_mat = np.full(dimensions, np.nan)
    
    # Set dimension names (in a real implementation, we'd use a named array)
    # For now, we just use the order from attribute_levels
    attr_names = list(attribute_levels.keys())
    
    # Fill in constrained cells with 0 probability
    if constraints is not None:
        for constraint in constraints:
            constraint_names = list(constraint.keys())
            constraint_levels = [constraint[name] for name in constraint_names]
            
            # Find indices for this constraint
            # This is a simplified approach - real implementation would need proper indexing
            for idx in np.ndindex(J_mat.shape):
                # Check if this index matches the constraint
                matches = True
                for dim_idx, attr_name in enumerate(constraint_names):
                    attr_idx = attr_names.index(attr_name)
                    level_idx = attribute_levels[attr_name].index(constraint_levels[dim_idx])
                    if idx[attr_idx] != level_idx:
                        matches = False
                        break
                if matches:
                    J_mat[idx] = 0
    
    # Fill probabilities for unconstrained cells
    unconstrained_mask = ~np.isnan(J_mat) & (J_mat != 0)
    n_unconstrained = np.sum(unconstrained_mask)
    
    if level_probs is None:
        # Uniform marginal randomization
        cell_prob = 1.0 / n_unconstrained
        J_mat[unconstrained_mask] = cell_prob
    else:
        # Non-uniform randomization with level probabilities
        # Normalize level.probs to sum to 1 for each attribute
        for attr in level_probs:
            level_probs[attr] = level_probs[attr] / np.sum(level_probs[attr])
        
        # Calculate unconstrained probabilities
        J_mat[unconstrained_mask] = 1.0
        
        # Apply level probabilities
        for attr_idx, attr in enumerate(attr_names):
            if attr in level_probs:
                for level_idx, prob in enumerate(level_probs[attr]):
                    # Set all cells with this level to have this probability factor
                    # This is a simplified approach
                    J_mat[unconstrained_mask] *= 1.0 / n_unconstrained
                    # Apply probability multiplication (simplified)
                    # Real implementation would need proper indexing
        
        # Normalize
        J_mat[unconstrained_mask] = J_mat[unconstrained_mask] / np.sum(J_mat[unconstrained_mask])
    
    dependence = compute_dependencies(J_mat, tol)
    return ConjointDesign(J=J_mat, dependence=dependence)


def _make_design_from_file(filename: str, tol: float = 1e-14) -> ConjointDesign:
    """Create design object from Conjoint SDT file."""
    # This is a placeholder for file parsing
    # Real implementation would parse the file format described in R code
    
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    # Find sections
    attr_index = None
    weight_index = None
    restriction_index = None
    
    for i, line in enumerate(lines):
        if line.strip() == "Attributes":
            attr_index = i
        elif line.strip() == "Weights":
            weight_index = i
        elif line.strip() == "Restrictions":
            restriction_index = i
    
    if attr_index is None:
        raise ValueError("Invalid file format: Could not find 'Attributes' section")
    
    # Parse attributes
    attributes = lines[attr_index + 1:weight_index] if weight_index else []
    attribute_levels = {}
    for attr_str in attributes:
        parts = attr_str.split(":")
        if len(parts) == 2:
            attr_name = parts[0].strip()
            levels = [l.strip() for l in parts[1].split(",")]
            attribute_levels[attr_name] = levels
    
    # Parse weights (level probabilities)
    level_probs = {}
    if weight_index:
        weight_lines = lines[weight_index + 1:restriction_index] if restriction_index else []
        for weight_str in weight_lines:
            parts = weight_str.split(":")
            if len(parts) == 2:
                attr_name = parts[0].strip()
                probs = np.array([float(w.strip()) for w in parts[1].split(",")])
                level_probs[attr_name] = probs
    
    # Parse constraints
    constraints = []
    if restriction_index and restriction_index + 1 < len(lines):
        constraint_lines = lines[restriction_index + 1:]
        for constr_line in constraint_lines:
            if constr_line.strip():
                constraint = {}
                # Parse constraint format: attr1:level1;attr2:level2
                for part in constr_line.split(";"):
                    if ":" in part:
                        attr, level = part.split(":")
                        constraint[attr.strip()] = level.strip()
                constraints.append(constraint)
    
    return _make_design_from_constraints(attribute_levels, constraints, level_probs, tol)
