from __future__ import annotations

import pandas as pd


def compute_factor(df: pd.DataFrame) -> pd.Series:
    """Return source-reported hospital stay duration in days."""
    if "time_in_hospital" not in df.columns:
        raise ValueError("Missing required column: time_in_hospital")
    return pd.to_numeric(df["time_in_hospital"], errors="coerce").astype("Float64")
