"""
pyjoint: Python implementation of the cjoint R package

This package provides tools for estimating Average Marginal Component Effects (AMCEs)
and Average Component Interaction Effects (ACIEs) from conjoint survey experiments.

Main functions:
    amce: Estimate AMCEs and ACIEs
    make_design: Create design matrices for non-uniform randomization
    summary_amce: Create summary tables of results
    plot_amce: Create coefficient plots
"""

__version__ = "0.1.0"
__author__ = "pyjoint development team"

from .estimator import amce, AMCEResult
from .design import make_design, compute_dependencies, ConjointDesign
from .summary import summary_amce, SummaryAMCE
from .plot import plot_amce
from .naming import clean_names, clean_names_vectorized
from .vcov import cluster_se_glm, fix_vcov, hc2_vcov

__all__ = [
    "amce",
    "AMCEResult",
    "make_design",
    "compute_dependencies",
    "ConjointDesign",
    "summary_amce",
    "SummaryAMCE",
    "plot_amce",
    "clean_names",
    "clean_names_vectorized",
    "cluster_se_glm",
    "fix_vcov",
    "hc2_vcov",
]
