from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
OUTPUT_DIR = PROJECT_DIR / "data" / "processed"
ENCOUNTERS_FILE = RAW_DIR / "diabetic_data.csv"
MAPPINGS_FILE = RAW_DIR / "IDS_mapping.csv"
OUTPUT_FILE = OUTPUT_DIR / "ehr_encounters.parquet"
REPORT_FILE = OUTPUT_DIR / "quality_report.json"

REQUIRED_COLUMNS = {
    "encounter_id",
    "patient_nbr",
    "admission_type_id",
    "discharge_disposition_id",
    "admission_source_id",
    "time_in_hospital",
    "readmitted",
}
MEDICATION_COLUMNS = [
    "metformin", "repaglinide", "nateglinide", "chlorpropamide",
    "glimepiride", "acetohexamide", "glipizide", "glyburide",
    "tolbutamide", "pioglitazone", "rosiglitazone", "acarbose",
    "miglitol", "troglitazone", "tolazamide", "examide",
    "citoglipton", "insulin", "glyburide_metformin",
    "glipizide_metformin", "glimepiride_pioglitazone",
    "metformin_rosiglitazone", "metformin_pioglitazone",
]


def normalize_header(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def read_mappings(path: Path) -> dict[str, dict[str, str]]:
    """Read IDS_mapping.csv, whose three lookup sections share one file."""
    if not path.exists():
        raise FileNotFoundError(f"Mapping CSV not found: {path}")

    mappings: dict[str, dict[str, str]] = defaultdict(dict)
    active_section: str | None = None
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.reader(handle):
            if not row:
                continue
            first = row[0].strip()
            second = row[1].strip() if len(row) > 1 else ""
            if first.endswith("_id") and second.lower() == "description":
                active_section = first
                continue
            if active_section and first.isdigit() and second:
                mappings[active_section][first] = second
    return dict(mappings)


def read_and_clean(path: Path) -> tuple[pd.DataFrame, int]:
    if not path.exists():
        raise FileNotFoundError(f"Encounter CSV not found: {path}")

    # Read as strings first: identifiers and categorical codes are labels, not
    # measurements. Convert specific quantitative fields only after cleanup.
    df = pd.read_csv(path, dtype="string", keep_default_na=False)
    df.columns = [normalize_header(str(column)) for column in df.columns]
    missing_required = REQUIRED_COLUMNS.difference(df.columns)
    if missing_required:
        raise ValueError("Required columns missing: " + ", ".join(sorted(missing_required)))

    # The dataset uses '?' for unavailable values. Blank cells also become null.
    # Keep the literal category 'None' because some result fields use it to mean
    # the measurement was not performed.
    for column in df.columns:
        values = df[column].str.strip()
        df[column] = values.mask(values.eq("") | values.eq("?"), pd.NA)

    df["encounter_id"] = df["encounter_id"].astype("string").str.strip()
    df["patient_nbr"] = df["patient_nbr"].astype("string").str.strip()

    numeric_columns = [
        "time_in_hospital", "num_lab_procedures", "num_procedures",
        "num_medications", "number_outpatient", "number_emergency",
        "number_inpatient", "number_diagnoses",
    ]
    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")

    input_rows = len(df)
    df = df.drop_duplicates(keep="first").copy()
    exact_duplicates_removed = input_rows - len(df)

    bad_encounter_id = df["encounter_id"].isna() | df["encounter_id"].eq("")
    if bad_encounter_id.any():
        raise ValueError(f"Found {int(bad_encounter_id.sum())} rows without encounter_id.")

    repeated_encounter = df["encounter_id"].duplicated(keep=False)
    repeated_count = int(repeated_encounter.sum())
    if repeated_count:
        raise ValueError(
            f"Found {repeated_count} rows with repeated encounter_id after exact-duplicate "
            "removal. Inspect and resolve these records explicitly before continuing."
        )

    return df, exact_duplicates_removed


def enrich_encounters(df: pd.DataFrame, mappings: dict[str, dict[str, str]]) -> pd.DataFrame:
    # Decode ID fields while preserving their original numeric/string codes.
    for source_column, output_column in (
        ("admission_type_id", "admission_type"),
        ("discharge_disposition_id", "discharge_disposition"),
        ("admission_source_id", "admission_source"),
    ):
        lookup = mappings.get(source_column, {})
        codes = df[source_column].astype("string")
        df[output_column] = codes.map(lookup).astype("string")

    available_medications = [column for column in MEDICATION_COLUMNS if column in df.columns]
    if available_medications:
        med_status = df[available_medications]
        known_status = med_status.notna()
        active_status = med_status.notna() & med_status.ne("No")
        df["medication_count_known"] = known_status.sum(axis=1).astype("Int64")
        df["medication_count"] = active_status.sum(axis=1).astype("Int64")
    else:
        df["medication_count_known"] = pd.Series(pd.NA, index=df.index, dtype="Int64")
        df["medication_count"] = pd.Series(pd.NA, index=df.index, dtype="Int64")

    if "readmitted" in df.columns:
        df["readmitted_within_30_days"] = df["readmitted"].eq("<30").astype("boolean")
    return df


def make_quality_report(
    df: pd.DataFrame,
    exact_duplicates_removed: int,
    mappings: dict[str, dict[str, str]],
) -> dict[str, Any]:
    missing_counts = {column: int(count) for column, count in df.isna().sum().items()}
    mapping_coverage: dict[str, dict[str, int]] = {}
    for id_column in ("admission_type_id", "discharge_disposition_id", "admission_source_id"):
        label_column = id_column.removesuffix("_id")
        if id_column in df.columns:
            code_mask = df[id_column].notna()
            mapping_coverage[id_column] = {
                "rows_with_code": int(code_mask.sum()),
                "rows_without_description": int((code_mask & df[label_column].isna()).sum()),
                "available_mapping_codes": len(mappings.get(id_column, {})),
            }

    return {
        "source_files": [ENCOUNTERS_FILE.name, MAPPINGS_FILE.name],
        "input_rows_after_exact_deduplication": int(len(df)),
        "exact_duplicate_rows_removed": exact_duplicates_removed,
        "unique_encounters": int(df["encounter_id"].nunique(dropna=True)),
        "unique_patients": int(df["patient_nbr"].nunique(dropna=True)),
        "missing_values_by_column": missing_counts,
        "mapping_coverage": mapping_coverage,
        "outputs": [str(OUTPUT_FILE), str(REPORT_FILE)],
        "note": "This is a learning ETL pipeline, not a clinical tool.",
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    mappings = read_mappings(MAPPINGS_FILE)
    encounters, exact_duplicates_removed = read_and_clean(ENCOUNTERS_FILE)
    encounters = enrich_encounters(encounters, mappings)

    encounters.to_parquet(OUTPUT_FILE, index=False)
    report = make_quality_report(encounters, exact_duplicates_removed, mappings)
    REPORT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Encounter rows saved: {len(encounters):,}")
    print(f"Unique patients: {encounters['patient_nbr'].nunique(dropna=True):,}")
    print(f"Exact duplicate rows removed: {exact_duplicates_removed:,}")
    print(f"Missing encounter IDs: {int(encounters['encounter_id'].isna().sum()):,}")
    print(f"Output Parquet: {OUTPUT_FILE}")
    print(f"Quality report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
