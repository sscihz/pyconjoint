"""
Plotting methods for pyjoint results.

This module replicates R's plot.amce function, creating coefficient plots
for AMCE and ACIE estimates using matplotlib.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import warnings
from typing import Dict, List, Optional, Union

from .estimator import AMCEResult


def plot_amce(
    object: AMCEResult,
    main: Optional[str] = None,
    xlab: str = "Effect on Probability",
    ylab: Optional[str] = None,
    ci: float = 0.95,
    colors: Optional[List[str]] = None,
    xlim: Optional[tuple] = None,
    breaks: Optional[List] = None,
    labels: Optional[List[str]] = None,
    attribute_names: Optional[Dict[str, str]] = None,
    level_names: Optional[Dict[str, str]] = None,
    label_baseline: bool = False,
    facet_names: Optional[List[str]] = None,
    facet_levels: Optional[List[str]] = None,
    plot_display: str = "all",
    show: bool = True
) -> plt.Figure:
    """
    Create coefficient plot of AMCE/ACIE estimates.
    
    Parameters
    ----------
    object : AMCEResult
        AMCE estimation result object
    main : str, optional
        Plot title
    xlab : str, default="Effect on Probability"
        X-axis label
    ylab : str, optional
        Y-axis label
    ci : float, default=0.95
        Confidence interval level
    colors : List[str], optional
        Custom colors for different attributes
    xlim : tuple, optional
        X-axis limits (min, max)
    breaks : List, optional
        X-axis tick marks
    labels : List[str], optional
        X-axis tick labels
    attribute_names : Dict[str, str], optional
        Mapping to rename attributes
    level_names : Dict[str, str], optional
        Mapping to rename levels
    label_baseline : bool, default=False
        Whether to label baseline levels
    facet_names : List[str], optional
        Variables to facet by
    facet_levels : List[str], optional
        Level names for facets
    plot_display : str, default="all"
        Which effects to display: "all", "unconditional", or "interaction"
    show : bool, default=True
        Whether to display the plot
        
    Returns
    -------
    plt.Figure
        Matplotlib figure object
        
    Examples
    --------
    >>> result = amce('y ~ x1 + x2', data)
    >>> fig = plot_amce(result)
    >>> plt.show()
    """
    # Calculate z-value for confidence interval
    z_value = norm.ppf(1 - (1 - ci) / 2)
    
    # Build plotting dataframe
    plot_data = _build_plot_data(object, ci, z_value)
    
    if plot_data.empty:
        warnings.warn("No estimates to plot")
        return None
    
    # Apply name mappings
    if attribute_names:
        plot_data['var'] = plot_data['var'].map(attribute_names).fillna(plot_data['var'])
    
    if level_names:
        plot_data['level'] = plot_data['level'].map(level_names).fillna(plot_data['level'])
    
    # Filter by plot_display
    if plot_display == "unconditional":
        plot_data = plot_data[plot_data['type'] == 'AMCE']
    elif plot_display == "interaction":
        plot_data = plot_data[plot_data['type'] == 'ACIE']
    
    if plot_data.empty:
        warnings.warn(f"No estimates to display for plot_display='{plot_display}'")
        return None
    
    # Create plot
    n_attributes = plot_data['var'].nunique()
    if n_attributes == 1:
        fig, axes = plt.subplots(1, 1, figsize=(8, 6))
        axes = np.array([axes])
    else:
        fig, axes = plt.subplots(n_attributes, 1, figsize=(8, 4 * n_attributes))
    
    for idx, (attr, attr_data) in enumerate(plot_data.groupby('var')):
        ax = axes[idx]
        
        # Plot confidence intervals
        for _, row in attr_data.iterrows():
            ax.errorbar(
                row['pe'],
                row['level'],
                xerr=row['se'] * z_value,
                fmt='o',
                capsize=5,
                capthick=2,
                markersize=8,
                color=colors[idx % len(colors)] if colors else 'steelblue'
            )
        
        # Add vertical line at zero
        ax.axvline(x=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
        
        # Set labels
        if ylab is None:
            ylab = attr
        ax.set_ylabel(ylab)
        ax.set_xlabel(xlab)
        
        # Set x-limits
        if xlim is not None:
            ax.set_xlim(xlim)
        else:
            x_min = attr_data['pe'].min() - 2 * attr_data['se'].max() * z_value
            x_max = attr_data['pe'].max() + 2 * attr_data['se'].max() * z_value
            ax.set_xlim(x_min, x_max)
        
        # Set x-ticks
        if breaks is not None:
            ax.set_xticks(breaks)
        if labels is not None:
            ax.set_xticklabels(labels)
        
        # Add baseline labels if requested
        if label_baseline:
            for var in object.baselines.keys():
                baseline = object.baselines[var]
                ax.axhline(y=baseline, color='gray', linestyle=':', alpha=0.5)
    
    # Set overall title
    if main is not None:
        fig.suptitle(main, y=0.995)
    
    plt.tight_layout()
    
    if show:
        plt.show()
    
    return fig


def _build_plot_data(object: AMCEResult, ci: float, z_value: float) -> pd.DataFrame:
    """Build dataframe for plotting from AMCEResult."""
    data_rows = []
    
    for var_name, var_estimates in object.estimates.items():
        # Determine if it's AMCE or ACIE
        if ':' in var_name:
            effect_type = 'ACIE'
            display_name = var_name
        else:
            effect_type = 'AMCE'
            display_name = var_name
        
        # Get estimates and SEs
        if 'AMCE' in var_estimates.index:
            for level in var_estimates.columns:
                pe = var_estimates.loc['AMCE', level]
                if not np.isnan(pe):
                    # Get SE (may need to square it if it's variance)
                    if 'Std. Error' in var_estimates.index:
                        se = np.sqrt(var_estimates.loc['Std. Error', level])
                    else:
                        se = 0.0
                    
                    # Calculate confidence interval
                    lower = pe - z_value * se
                    upper = pe + z_value * se
                    
                    data_rows.append({
                        'var': display_name,
                        'level': level,
                        'pe': pe,
                        'se': se,
                        'lower': lower,
                        'upper': upper,
                        'type': effect_type
                    })
    
    return pd.DataFrame(data_rows)


# Add plot method to AMCEResult class
def plot(self, **kwargs) -> plt.Figure:
    """
    Plot method for AMCEResult.
    
    Parameters
    ----------
    **kwargs
        Additional arguments passed to plot_amce
    """
    return plot_amce(self, **kwargs)


AMCEResult.plot = plot


# Import scipy.stats.norm at module level
from scipy.stats import norm
