from __future__ import annotations

import pandas as pd


def compute_factor(df: pd.DataFrame) -> pd.Series:
    """Return the medication count calculated by ehr_pipeline.py."""
    if "medication_count" not in df.columns:
        raise ValueError(
            "Missing medication_count. Run ehr_pipeline.py first to enrich encounters."
        )
    return pd.to_numeric(df["medication_count"], errors="coerce").astype("Float64")
