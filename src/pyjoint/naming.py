"""
String cleaning and naming utilities for pyjoint.

This module replicates R's clean.names function which removes punctuation,
symbols, and spaces from variable names for safe processing.
"""

import re
import unicodedata
from typing import List, Union


def clean_names(s: str) -> str:
    """
    Remove all punctuation, symbols, and spaces from a string.
    
    This replicates R's clean.names function:
        gsub("[\\p{P}\\p{S}\\p{Z}]","",x,perl=T)
    
    Parameters
    ----------
    s : str
        The input string to clean
        
    Returns
    -------
    str
        The cleaned string with all punctuation, symbols, and spaces removed
        
    Examples
    --------
    >>> clean_names("Education Level")
    'EducationLevel'
    >>> clean_names("Country of Origin")
    'CountryofOrigin'
    >>> clean_names("Education:Language Skills")
    'Education:LanguageSkills'
    """
    # Python's stdlib `re` does not support Unicode \p categories, so filter
    # by Unicode category instead.
    return "".join(
        ch for ch in s if unicodedata.category(ch)[0] not in {"P", "S", "Z"}
    )


def clean_names_vectorized(strings: List[str]) -> List[str]:
    """
    Apply clean_names to a list/vector of strings.
    
    This replicates R's Vectorize(clean.names, vectorize.args=("str"), USE.NAMES = F)
    
    Parameters
    ----------
    strings : List[str]
        List of strings to clean
        
    Returns
    -------
    List[str]
        List of cleaned strings
        
    Examples
    --------
    >>> clean_names_vectorized(["Gender", "Education Level", "Country"])
    ['Gender', 'EducationLevel', 'Country']
    """
    return [clean_names(s) for s in strings]


def split_interaction_term(term: str) -> List[str]:
    """
    Split an interaction term into its components.
    
    Parameters
    ----------
    term : str
        Interaction term like "A:B" or "A*B"
        
    Returns
    -------
    List[str]
        List of component variable names
        
    Examples
    --------
    >>> split_interaction_term("Education:LanguageSkills")
    ['Education', 'LanguageSkills']
    >>> split_interaction_term("A*B")
    ['A', 'B']
    """
    # Split by either : or * (both used for interactions)
    return re.split(r'[:*]', term)


def create_coef_name(var_name: str, level: str) -> str:
    """
    Create a coefficient name from variable name and level.
    
    In R, factor levels are represented as concatenated names like:
    varnamelevelname
    
    Parameters
    ----------
    var_name : str
        The variable name
    level : str
        The level name (already cleaned)
        
    Returns
    -------
    str
        The coefficient name
        
    Examples
    --------
    >>> create_coef_name("Gender", "Female")
    'GenderFemale'
    """
    return var_name + level


def validate_unique_names(names: List[str]) -> None:
    """
    Validate that cleaned names are unique.
    
    Parameters
    ----------
    names : List[str]
        List of cleaned names to validate
        
    Raises
    ------
    ValueError
        If names are not unique after cleaning
        
    Examples
    --------
    >>> validate_unique_names(['Var1', 'Var2'])  # OK
    >>> validate_unique_names(['Var1', 'Var1'])  # Raises ValueError
    """
    unique_names = set(names)
    if len(unique_names) != len(names):
        raise ValueError(
            "Variable names must be unique when whitespace and "
            "meta-characters are removed. Please rename."
        )


def validate_unique_levels(var_name: str, levels: List[str]) -> None:
    """
    Validate that levels are unique after cleaning.
    
    Parameters
    ----------
    var_name : str
        The variable name (for error message)
    levels : List[str]
        List of levels to validate (already cleaned)
        
    Raises
    ------
    ValueError
        If levels are not unique after cleaning
        
    Examples
    --------
    >>> validate_unique_levels('Gender', ['Male', 'Female'])  # OK
    >>> validate_unique_levels('Var', ['Level1', 'Level1'])  # Raises ValueError
    """
    unique_levels = set(levels)
    if len(unique_levels) != len(levels):
        raise ValueError(
            f"Levels of variable {var_name} are not unique when whitespace "
            "and meta-characters are removed. Please rename."
        )
