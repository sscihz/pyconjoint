"""
Summary and display methods for pyjoint results.

This module replicates R's summary.amce function, providing formatted
tables of AMCE and ACIE estimates with significance tests.
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Optional
from dataclasses import dataclass

from .estimator import AMCEResult


@dataclass
class SummaryAMCE:
    """
    Summary object for AMCE results.
    
    Attributes
    ----------
    amce : pd.DataFrame
        Table of AMCE estimates
    acie : Optional[pd.DataFrame]
        Table of ACIE estimates (if present)
    baselines_amce : Dict[str, str]
        Baseline levels for AMCE
    baselines_acie : Optional[Dict[str, str]]
        Baseline levels for ACIE
    samplesize_estimates : int
        Sample size used for estimation
    samplesize_resp : Optional[int]
        Sample size with respondent effects
    respondents : Optional[int]
        Number of respondents
    """
    amce: pd.DataFrame
    acie: Optional[pd.DataFrame] = None
    baselines_amce: Dict[str, str] = None
    baselines_acie: Optional[Dict[str, str]] = None
    samplesize_estimates: int = None
    samplesize_resp: Optional[int] = None
    respondents: Optional[int] = None


def summary_amce(
    object: AMCEResult,
    ci_level: float = 0.95
) -> SummaryAMCE:
    """
    Create summary of AMCE/ACIE estimation results.
    
    Parameters
    ----------
    object : AMCEResult
        AMCE estimation result object
    ci_level : float, default=0.95
        Confidence level for intervals
        
    Returns
    -------
    SummaryAMCE
        Summary object with formatted tables
        
    Examples
    --------
    >>> result = amce('y ~ x1 + x2', data)
    >>> summ = summary_amce(result)
    >>> print(summ)
    """
    # Extract AMCE estimates
    amce_estimates = []
    amce_var_names = []
    
    for var_name, var_estimates in object.estimates.items():
        # Check if this is a main effect (not interaction)
        if ':' not in var_name:
            levels = var_estimates.columns
            for level in levels:
                est = var_estimates.loc['AMCE', level]
                if not np.isnan(est):
                    # Calculate SE, z, p-value
                    se = np.sqrt(var_estimates.loc['Std. Error', level]) if 'Std. Error' in var_estimates.index else np.nan
                    if not np.isnan(se) and se > 0:
                        z = est / se
                        p = 2 * (1 - stats.norm.cdf(abs(z)))
                        
                        # Add significance stars
                        sig = ''
                        if p < 0.01:
                            sig = '***'
                        elif p < 0.05:
                            sig = '**'
                        elif p < 0.1:
                            sig = '*'
                    else:
                        z = np.nan
                        p = np.nan
                        sig = ''
                    
                    amce_estimates.append({
                        'Attribute': var_name,
                        'Level': level,
                        'Estimate': est,
                        'Std. Error': se,
                        'z': z,
                        'p': p,
                        'Sig': sig
                    })
    
    # Create AMCE summary table
    amce_df = pd.DataFrame(amce_estimates)
    if not amce_df.empty:
        # Round numeric columns
        amce_df['Estimate'] = amce_df['Estimate'].round(4)
        amce_df['Std. Error'] = amce_df['Std. Error'].round(4)
        amce_df['z'] = amce_df['z'].round(3)
        amce_df['p'] = amce_df['p'].round(3)
    
    # Extract ACIE estimates if present
    acie_df = None
    acie_estimates = []
    
    for var_name, var_estimates in object.estimates.items():
        # Check if this is an interaction
        if ':' in var_name:
            levels = var_estimates.columns
            for level in levels:
                est = var_estimates.loc['AMCE', level] if 'AMCE' in var_estimates.index else np.nan
                if not np.isnan(est):
                    se = np.sqrt(var_estimates.loc['Std. Error', level]) if 'Std. Error' in var_estimates.index else np.nan
                    if not np.isnan(se) and se > 0:
                        z = est / se
                        p = 2 * (1 - stats.norm.cdf(abs(z)))
                        
                        sig = ''
                        if p < 0.01:
                            sig = '***'
                        elif p < 0.05:
                            sig = '**'
                        elif p < 0.1:
                            sig = '*'
                    else:
                        z = np.nan
                        p = np.nan
                        sig = ''
                    
                    acie_estimates.append({
                        'Interaction': var_name,
                        'Level': level,
                        'Estimate': est,
                        'Std. Error': se,
                        'z': z,
                        'p': p,
                        'Sig': sig
                    })
    
    if acie_estimates:
        acie_df = pd.DataFrame(acie_estimates)
        if not acie_df.empty:
            acie_df['Estimate'] = acie_df['Estimate'].round(4)
            acie_df['Std. Error'] = acie_df['Std. Error'].round(4)
            acie_df['z'] = acie_df['z'].round(3)
            acie_df['p'] = acie_df['p'].round(3)
    
    return SummaryAMCE(
        amce=amce_df,
        acie=acie_df,
        baselines_amce=object.baselines,
        samplesize_estimates=object.samplesize_prof,
        respondents=object.numrespondents
    )


def print_summary(summary_obj: SummaryAMCE) -> None:
    """
    Print formatted summary of AMCE results.
    
    Parameters
    ----------
    summary_obj : SummaryAMCE
        Summary object to print
    """
    print("\n" + "="*80)
    print("AMCE ESTIMATION SUMMARY")
    print("="*80)
    
    print("\nSample Size:", summary_obj.samplesize_estimates)
    if summary_obj.respondents:
        print("Number of Respondents:", summary_obj.respondents)
    
    if summary_obj.baselines_amce:
        print("\nBaselines:")
        for var, baseline in summary_obj.baselines_amce.items():
            print(f"  {var}: {baseline}")
    
    if not summary_obj.amce.empty:
        print("\n" + "-"*80)
        print("AVERAGE MARGINAL COMPONENT EFFECTS (AMCEs)")
        print("-"*80)
        print(summary_obj.amce.to_string(index=False))
    
    if summary_obj.acie is not None and not summary_obj.acie.empty:
        print("\n" + "-"*80)
        print("AVERAGE COMPONENT INTERACTION EFFECTS (ACIEs)")
        print("-"*80)
        print(summary_obj.acie.to_string(index=False))
    
    print("\n" + "="*80)
    print("Significance codes: 0 '***' 0.001 '**' 0.01 '*' 0.05 '.' 0.1 ' ' 1")
    print("="*80 + "\n")


# S3-like method for AMCEResult
def summary(self: AMCEResult, ci_level: float = 0.95) -> SummaryAMCE:
    """
    Summary method for AMCEResult.
    
    Parameters
    ----------
    ci_level : float, default=0.95
        Confidence level
    """
    return summary_amce(self, ci_level=ci_level)


# Add method to AMCEResult class
AMCEResult.summary = summary
