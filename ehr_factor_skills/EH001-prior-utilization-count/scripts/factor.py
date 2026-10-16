from __future__ import annotations

import pandas as pd


def compute_factor(df: pd.DataFrame) -> pd.Series:
    """Return prior utilization count for each encounter."""
    columns = ["number_outpatient", "number_emergency", "number_inpatient"]
    missing = set(columns).difference(df.columns)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
    values = df[columns].apply(pd.to_numeric, errors="coerce")
    # Keep the result missing when all three source counts are missing.
    return values.sum(axis=1, min_count=1).astype("Float64")
