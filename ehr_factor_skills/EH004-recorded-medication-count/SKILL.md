# EH004 — Recorded Medication Count

## Purpose

Count derived by the EHR ETL pipeline; missing medication statuses are not counted as No.

This is a descriptive educational feature for encounter-level data. It is not a validated clinical score, treatment recommendation, or patient risk assessment.

## Stable identifier

`EH004`

## Formula

`count medication fields with a recorded status other than No`

## Input contract

The `compute_factor(df)` function expects a pandas DataFrame with these columns:

- `medication_count`

It returns one pandas Series aligned to the input rows. Missing or invalid numeric inputs remain missing. A zero hospital stay does not produce an infinite rate; the rate is missing for that row.

## Run

```python
import importlib.util
import pandas as pd

factor_file = r"EH004-recorded-medication-count\scripts\factor.py"
spec = importlib.util.spec_from_file_location("ehr_factor", factor_file)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
encounters = pd.read_parquet(r"data\processed\ehr_encounters.parquet")
values = module.compute_factor(encounters)
```

## Limitations

This field describes columns in the historical UCI research dataset. Its meaning depends on the source definitions and completeness. It should not be interpreted as a clinical judgment or used to guide care.
