import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyjoint

ROOT = Path(__file__).resolve().parents[1]


def _load_levels():
    with open(ROOT / "data/immigrationconjoint_levels.json", "r") as f:
        return json.load(f)


def _load_expected():
    with open(ROOT / "data/cjoint_expected_results.json", "r") as f:
        return json.load(f)


def _load_data():
    df = pd.read_csv(ROOT / "data/immigrationconjoint.csv")
    levels = _load_levels()
    for col, cats in levels.items():
        if col in df.columns:
            df[col] = pd.Categorical(df[col], categories=cats, ordered=True)
    return df, levels


def _var_map(levels):
    return {pyjoint.clean_names(name): name for name in levels}


def _pyjoint_terms(result, levels):
    mapping = _var_map(levels)
    rows = []
    for var, table in result.estimates.items():
        orig_var = mapping.get(var, var)
        for col in table.columns:
            est = table.loc["AMCE", col]
            if pd.isna(est):
                continue
            level = col[len(var):]
            term = f"{orig_var}:{level}"
            rows.append(
                {
                    "term": term,
                    "estimate": float(est),
                    "std_error": float(table.loc["Std. Error", col]),
                }
            )
    return pd.DataFrame(rows)


def _compare_terms(actual_df, expected_list, tol=1e-3):
    expected_df = pd.DataFrame(expected_list)
    merged = actual_df.merge(expected_df, on="term", suffixes=("_py", "_r"))
    assert not merged.empty, "No overlapping terms found between pyjoint and cjoint results."
    max_est = np.max(np.abs(merged["estimate_py"] - merged["estimate_r"]))
    max_se = np.max(np.abs(merged["std_error_py"] - merged["std_error_r"]))
    assert max_est <= tol, f"Max estimate diff {max_est:.6f} exceeds {tol}"
    assert max_se <= tol, f"Max std err diff {max_se:.6f} exceeds {tol}"


def test_amce_cluster_matches_cjoint():
    df, levels = _load_data()
    result = pyjoint.amce(
        formula="Chosen_Immigrant ~ Gender + Education + Country of Origin + Language Skills",
        data=df,
        respondent_id="CaseID",
        cluster=True,
    )
    expected = _load_expected()["cluster"]
    actual = _pyjoint_terms(result, levels)
    _compare_terms(actual, expected, tol=2e-3)


def test_amce_no_cluster_matches_cjoint():
    df, levels = _load_data()
    result = pyjoint.amce(
        formula="Chosen_Immigrant ~ Gender + Education + Country of Origin + Language Skills",
        data=df,
        respondent_id=None,
        cluster=False,
    )
    expected = _load_expected()["no_cluster"]
    actual = _pyjoint_terms(result, levels)
    _compare_terms(actual, expected, tol=2e-3)


def test_amce_weights_matches_cjoint():
    df, levels = _load_data()
    weights = pd.read_csv(ROOT / "data/immigrationconjoint_weights.csv")
    df["weights"] = weights["weights"].values
    result = pyjoint.amce(
        formula="Chosen_Immigrant ~ Gender + Education + Country of Origin + Language Skills",
        data=df,
        respondent_id="CaseID",
        cluster=True,
        weights="weights",
    )
    expected = _load_expected()["weights"]
    actual = _pyjoint_terms(result, levels)
    _compare_terms(actual, expected, tol=4e-3)
