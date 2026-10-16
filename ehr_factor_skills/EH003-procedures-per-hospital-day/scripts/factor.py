from __future__ import annotations

import pandas as pd


def compute_factor(df: pd.DataFrame) -> pd.Series:
    """Return recorded procedures divided by hospital days."""
    required = {"num_procedures", "time_in_hospital"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
    numerator = pd.to_numeric(df["num_procedures"], errors="coerce")
    denominator = pd.to_numeric(df["time_in_hospital"], errors="coerce")
    denominator = denominator.where(denominator > 0)
    return (numerator / denominator).astype("Float64")
