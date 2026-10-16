# EH001 — Prior Utilization Count

## Purpose

Sum of the three prior-visit count fields supplied in the source dataset.

This is a descriptive educational feature for encounter-level data. It is not a validated clinical score, treatment recommendation, or patient risk assessment.

## Stable identifier

`EH001`

## Formula

`number_outpatient + number_emergency + number_inpatient`

## Input contract

The `compute_factor(df)` function expects a pandas DataFrame with these columns:

- `number_outpatient`
- `number_emergency`
- `number_inpatient`

It returns one pandas Series aligned to the input rows. Missing or invalid numeric inputs remain missing. A zero hospital stay does not produce an infinite rate; the rate is missing for that row.

## Run

```python
import importlib.util
import pandas as pd

factor_file = r"EH001-prior-utilization-count\scripts\factor.py"
spec = importlib.util.spec_from_file_location("ehr_factor", factor_file)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
encounters = pd.read_parquet(r"data\processed\ehr_encounters.parquet")
values = module.compute_factor(encounters)
```

## Limitations

This field describes columns in the historical UCI research dataset. Its meaning depends on the source definitions and completeness. It should not be interpreted as a clinical judgment or used to guide care.
