# Method comparison

Formula used:

- `Chosen_Immigrant ~ Gender + Education + Country of Origin + Language Skills`

## cjoint (R) vs pyjoint (Python)

| Method | Max |Δ| estimate | Max |Δ| std. error |
| --- | --- | --- |
| cluster | 0.000046 | 0.000050 |
| no_cluster | 0.000046 | 0.000045 |
| weights | 0.000042 | 0.003444 |

## pyjoint method deltas (internal)

| Comparison | Max |Δ| estimate | Max |Δ| std. error |
| --- | --- | --- |
| cluster vs no_cluster | 0.000000 | 0.000565 |
