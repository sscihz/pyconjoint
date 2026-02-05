import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyjoint

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORT = ROOT / "reports" / "method_comparison.md"


def load_levels():
    with open(DATA / "immigrationconjoint_levels.json", "r") as f:
        return json.load(f)


def load_expected():
    with open(DATA / "cjoint_expected_results.json", "r") as f:
        return json.load(f)


def load_data():
    df = pd.read_csv(DATA / "immigrationconjoint.csv")
    levels = load_levels()
    for col, cats in levels.items():
        if col in df.columns:
            df[col] = pd.Categorical(df[col], categories=cats, ordered=True)
    return df, levels


def var_map(levels):
    return {pyjoint.clean_names(name): name for name in levels}


def pyjoint_terms(result, levels):
    mapping = var_map(levels)
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


def compare(actual_df, expected_list):
    expected_df = pd.DataFrame(expected_list)
    merged = actual_df.merge(expected_df, on="term", suffixes=("_py", "_r"))
    max_est = np.max(np.abs(merged["estimate_py"] - merged["estimate_r"]))
    max_se = np.max(np.abs(merged["std_error_py"] - merged["std_error_r"]))
    return max_est, max_se


def main():
    df, levels = load_data()
    expected = load_expected()

    formula = "Chosen_Immigrant ~ Gender + Education + Country of Origin + Language Skills"

    cluster_res = pyjoint.amce(
        formula=formula,
        data=df,
        respondent_id="CaseID",
        cluster=True,
    )
    no_cluster_res = pyjoint.amce(
        formula=formula,
        data=df,
        respondent_id=None,
        cluster=False,
    )

    weights = pd.read_csv(DATA / "immigrationconjoint_weights.csv")
    df_weights = df.copy()
    df_weights["weights"] = weights["weights"].values
    weights_res = pyjoint.amce(
        formula=formula,
        data=df_weights,
        respondent_id="CaseID",
        cluster=True,
        weights="weights",
    )

    rows = []
    for name, res, exp_key in [
        ("cluster", cluster_res, "cluster"),
        ("no_cluster", no_cluster_res, "no_cluster"),
        ("weights", weights_res, "weights"),
    ]:
        actual = pyjoint_terms(res, levels)
        max_est, max_se = compare(actual, expected[exp_key])
        rows.append((name, max_est, max_se))

    # Compare pyjoint method deltas (cluster vs no_cluster)
    cluster_terms = pyjoint_terms(cluster_res, levels)
    no_cluster_terms = pyjoint_terms(no_cluster_res, levels)
    merged = cluster_terms.merge(no_cluster_terms, on="term", suffixes=("_cluster", "_no"))
    method_est = np.max(np.abs(merged["estimate_cluster"] - merged["estimate_no"]))
    method_se = np.max(np.abs(merged["std_error_cluster"] - merged["std_error_no"]))

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT, "w") as f:
        f.write("# Method comparison\n\n")
        f.write("Formula used:\n\n")
        f.write(f"- `{formula}`\n\n")
        f.write("## cjoint (R) vs pyjoint (Python)\n\n")
        f.write("| Method | Max |Δ| estimate | Max |Δ| std. error |\n")
        f.write("| --- | --- | --- |\n")
        for name, max_est, max_se in rows:
            f.write(f"| {name} | {max_est:.6f} | {max_se:.6f} |\n")
        f.write("\n")
        f.write("## pyjoint method deltas (internal)\n\n")
        f.write("| Comparison | Max |Δ| estimate | Max |Δ| std. error |\n")
        f.write("| --- | --- | --- |\n")
        f.write(
            f"| cluster vs no_cluster | {method_est:.6f} | {method_se:.6f} |\n"
        )


if __name__ == "__main__":
    main()
