from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from ehr_factor_pipeline import FACTOR_DEFINITIONS


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_ROOT = PROJECT_DIR / "ehr_factor_skills"

# Each compute_factor(df) function returns one pandas Series aligned to df.index.
# Formulas mirror the calculations in ehr_factor_pipeline.py.
FACTOR_CODE: dict[str, str] = {
    "EH001": '''from __future__ import annotations

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
''',
    "EH002": '''from __future__ import annotations

import pandas as pd


def compute_factor(df: pd.DataFrame) -> pd.Series:
    """Return recorded lab procedures divided by hospital days."""
    required = {"num_lab_procedures", "time_in_hospital"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
    numerator = pd.to_numeric(df["num_lab_procedures"], errors="coerce")
    denominator = pd.to_numeric(df["time_in_hospital"], errors="coerce")
    denominator = denominator.where(denominator > 0)
    return (numerator / denominator).astype("Float64")
''',
    "EH003": '''from __future__ import annotations

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
''',
    "EH004": '''from __future__ import annotations

import pandas as pd


def compute_factor(df: pd.DataFrame) -> pd.Series:
    """Return the medication count calculated by ehr_pipeline.py."""
    if "medication_count" not in df.columns:
        raise ValueError(
            "Missing medication_count. Run ehr_pipeline.py first to enrich encounters."
        )
    return pd.to_numeric(df["medication_count"], errors="coerce").astype("Float64")
''',
    "EH005": '''from __future__ import annotations

import pandas as pd


def compute_factor(df: pd.DataFrame) -> pd.Series:
    """Return source-reported hospital stay duration in days."""
    if "time_in_hospital" not in df.columns:
        raise ValueError("Missing required column: time_in_hospital")
    return pd.to_numeric(df["time_in_hospital"], errors="coerce").astype("Float64")
''',
}


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def factor_folder_name(factor: dict[str, Any]) -> str:
    return f"{factor['factor_id']}-{slugify(factor['name'])}"


def make_skill_md(factor: dict[str, Any], required_columns: list[str]) -> str:
    return f'''# {factor['factor_id']} — {factor['name']}

## Purpose

{factor['description']}

This is a descriptive educational feature for encounter-level data. It is not a validated clinical score, treatment recommendation, or patient risk assessment.

## Stable identifier

`{factor['factor_id']}`

## Formula

`{factor['formula']}`

## Input contract

The `compute_factor(df)` function expects a pandas DataFrame with these columns:

{chr(10).join(f'- `{column}`' for column in required_columns)}

It returns one pandas Series aligned to the input rows. Missing or invalid numeric inputs remain missing. A zero hospital stay does not produce an infinite rate; the rate is missing for that row.

## Run

```python
import importlib.util
import pandas as pd

factor_file = r"{factor_folder_name(factor)}\\scripts\\factor.py"
spec = importlib.util.spec_from_file_location("ehr_factor", factor_file)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
encounters = pd.read_parquet(r"data\\processed\\ehr_encounters.parquet")
values = module.compute_factor(encounters)
```

## Limitations

This field describes columns in the historical UCI research dataset. Its meaning depends on the source definitions and completeness. It should not be interpreted as a clinical judgment or used to guide care.
'''


def make_formula_md(factor: dict[str, Any], required_columns: list[str]) -> str:
    return f'''# Formula reference: {factor['factor_id']}

- **Name:** {factor['name']}
- **Output column:** `{factor['column']}`
- **Formula:** `{factor['formula']}`
- **Unit:** {factor['unit']}
- **Required input columns:** {', '.join(f'`{column}`' for column in required_columns)}
- **Missing values:** invalid or missing numeric values produce a missing output. No value is clinically imputed.

The implementation in `scripts/factor.py` is intended to match the corresponding calculation in `ehr_factor_pipeline.py`.
'''


def factor_required_columns(factor_id: str, column: str) -> list[str]:
    required = {
        "EH001": ["number_outpatient", "number_emergency", "number_inpatient"],
        "EH002": ["num_lab_procedures", "time_in_hospital"],
        "EH003": ["num_procedures", "time_in_hospital"],
        "EH004": ["medication_count"],
        "EH005": ["time_in_hospital"],
    }
    if factor_id not in required:
        raise ValueError(f"No factor implementation template exists for {factor_id} ({column}).")
    return required[factor_id]


def build_package(output_root: Path, overwrite: bool) -> None:
    missing_templates = {item["factor_id"] for item in FACTOR_DEFINITIONS} - set(FACTOR_CODE)
    if missing_templates:
        raise ValueError("Missing code templates for: " + ", ".join(sorted(missing_templates)))

    existing_index = output_root / "factor_index.json"
    if output_root.exists() and existing_index.exists() and not overwrite:
        raise FileExistsError(
            f"{existing_index} already exists. Choose another --output-root or pass --overwrite "
            "to refresh generated files. Existing unrelated files will not be deleted."
        )

    output_root.mkdir(parents=True, exist_ok=True)
    index: list[dict[str, Any]] = []
    for factor in FACTOR_DEFINITIONS:
        factor_id = factor["factor_id"]
        slug = slugify(factor["name"])
        folder_name = factor_folder_name(factor)
        factor_dir = output_root / folder_name
        required = factor_required_columns(factor_id, factor["column"])
        (factor_dir / "scripts").mkdir(parents=True, exist_ok=True)
        (factor_dir / "references").mkdir(parents=True, exist_ok=True)

        (factor_dir / "scripts" / "factor.py").write_text(FACTOR_CODE[factor_id], encoding="utf-8")
        (factor_dir / "SKILL.md").write_text(make_skill_md(factor, required), encoding="utf-8")
        (factor_dir / "references" / "formula.md").write_text(
            make_formula_md(factor, required), encoding="utf-8"
        )

        index.append(
            {
                "factor_id": factor_id,
                "slug": slug,
                "name_en": factor["name"],
                "category_en": "Encounter descriptor",
                "column": factor["column"],
                "formula_en": factor["formula"],
                "rationale_en": factor["description"],
                "unit": factor["unit"],
                "record_level": "encounter",
                "clinical_use": False,
                "path": folder_name,
            }
        )

    (output_root / "factor_index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    readme = '''# EHR Factor Practice Package\n\nThis package contains descriptive encounter-level feature examples generated from `ehr_factor_pipeline.py`.\n\n- `factor_index.json` lists the stable IDs and metadata.\n- Each `EH###-...` directory contains `SKILL.md`, `scripts/factor.py`, and `references/formula.md`.\n- The functions accept the cleaned encounter table and return values aligned to its rows.\n\nThese are educational features, not validated clinical scores or tools for patient care. See the project guide and the UCI dataset citation before sharing derived work.\n'''
    (output_root / "README.md").write_text(readme, encoding="utf-8")

    print(f"Factor folders created or refreshed: {len(index)}")
    print(f"Factor package: {output_root}")
    print(f"Index: {existing_index}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build one reusable factor folder for each factor in ehr_factor_pipeline.py."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=f"Package output folder (default: {DEFAULT_OUTPUT_ROOT})",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Refresh generated factor files in the output folder; unrelated files are kept.",
    )
    args = parser.parse_args()
    build_package(args.output_root.resolve(), args.overwrite)


if __name__ == "__main__":
    main()
