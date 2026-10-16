from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
INPUT_FILE = PROJECT_DIR / "data" / "processed" / "ehr_encounters.parquet"
OUTPUT_DIR = PROJECT_DIR / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "ehr_factor_values.parquet"
CATALOG_FILE = OUTPUT_DIR / "ehr_factor_catalog.json"

# Each item documents a descriptive derived field. These are educational
# encounter-level features, not validated clinical scores or recommendations.
FACTOR_DEFINITIONS: list[dict[str, Any]] = [
    {
        "factor_id": "EH001",
        "name": "Prior Utilization Count",
        "column": "prior_utilization_count",
        "formula": "number_outpatient + number_emergency + number_inpatient",
        "description": "Sum of the three prior-visit count fields supplied in the source dataset.",
        "unit": "count",
    },
    {
        "factor_id": "EH002",
        "name": "Lab Procedures per Hospital Day",
        "column": "lab_procedures_per_day",
        "formula": "num_lab_procedures / time_in_hospital when time_in_hospital > 0",
        "description": "Descriptive rate of recorded lab procedures over the encounter's hospital days.",
        "unit": "procedures per day",
    },
    {
        "factor_id": "EH003",
        "name": "Procedures per Hospital Day",
        "column": "procedures_per_day",
        "formula": "num_procedures / time_in_hospital when time_in_hospital > 0",
        "description": "Descriptive rate of recorded procedures over the encounter's hospital days.",
        "unit": "procedures per day",
    },
    {
        "factor_id": "EH004",
        "name": "Recorded Medication Count",
        "column": "medication_count",
        "formula": "count medication fields with a recorded status other than No",
        "description": "Count derived by the EHR ETL pipeline; missing medication statuses are not counted as No.",
        "unit": "count",
    },
    {
        "factor_id": "EH005",
        "name": "Hospital Stay Days",
        "column": "time_in_hospital",
        "formula": "time_in_hospital",
        "description": "Length of stay in days as provided by the source dataset (not an admission date).",
        "unit": "days",
    },
]


def require_columns(frame: pd.DataFrame, columns: set[str]) -> None:
    missing = columns.difference(frame.columns)
    if missing:
        raise ValueError(
            "Input Parquet is missing required columns: "
            + ", ".join(sorted(missing))
        )


def numeric_column(frame: pd.DataFrame, name: str) -> pd.Series:
    if name not in frame.columns:
        return pd.Series(pd.NA, index=frame.index, dtype="Float64")
    return pd.to_numeric(frame[name], errors="coerce").astype("Float64")


def generate_factors(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"encounter_id", "time_in_hospital"}
    require_columns(frame, required)

    out = pd.DataFrame(index=frame.index)
    # Keep encounter_id for joining the factor values back to the encounter
    # table. Patient identifiers and readmission outcomes are deliberately
    # omitted from this factor output.
    out["encounter_id"] = frame["encounter_id"].astype("string")

    prior_fields = ["number_outpatient", "number_emergency", "number_inpatient"]
    prior_values = pd.concat(
        [numeric_column(frame, name) for name in prior_fields], axis=1
    )
    out["prior_utilization_count"] = prior_values.sum(axis=1, min_count=1).astype("Float64")

    stay_days = numeric_column(frame, "time_in_hospital")
    lab_count = numeric_column(frame, "num_lab_procedures")
    procedure_count = numeric_column(frame, "num_procedures")
    valid_stay = stay_days.where(stay_days > 0)
    out["lab_procedures_per_day"] = (lab_count / valid_stay).astype("Float64")
    out["procedures_per_day"] = (procedure_count / valid_stay).astype("Float64")

    out["medication_count"] = numeric_column(frame, "medication_count")
    out["time_in_hospital"] = stay_days

    # Retain a stable, readable order for downstream inspection.
    return out[["encounter_id", *[item["column"] for item in FACTOR_DEFINITIONS]]]


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Cleaned EHR Parquet not found: {INPUT_FILE}\n"
            "Run ehr_pipeline.py first to create it."
        )

    encounters = pd.read_parquet(INPUT_FILE)
    factors = generate_factors(encounters)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    factors.to_parquet(OUTPUT_FILE, index=False)
    CATALOG_FILE.write_text(
        json.dumps(
            {
                "title": "EHR Encounter Practice Factors",
                "source_file": str(INPUT_FILE),
                "output_file": str(OUTPUT_FILE),
                "level": "encounter",
                "clinical_use": False,
                "factors": FACTOR_DEFINITIONS,
                "notes": [
                    "These are descriptive educational features, not validated clinical scores.",
                    "No patient identifier or readmission outcome is included in the factor output.",
                    "The source dataset has no encounter date field; none is invented here.",
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Encounters processed: {len(factors):,}")
    print(f"Factor fields created: {len(FACTOR_DEFINITIONS)}")
    print(f"Factor Parquet: {OUTPUT_FILE}")
    print(f"Factor catalog: {CATALOG_FILE}")


if __name__ == "__main__":
    main()
