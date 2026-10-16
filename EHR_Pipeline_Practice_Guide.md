# EHR Data Pipeline Practice: Diabetes Hospital Encounters

This guided practice builds a small ETL pipeline from the UCI Diabetes 130-US Hospitals dataset already placed in `data\raw`:

- `diabetic_data.csv`
- `IDS_mapping.csv`

It follows **read → clean → check → enrich → save** and writes a Parquet file plus a quality report. This is a data-engineering exercise only. It does not make clinical recommendations, and its output should not be used for patient care or operational decisions.

## About this dataset

The dataset contains 101,766 hospital encounter records for people with diabetes from 130 US hospitals during 1999–2008. Each row is an encounter, and a patient can have multiple encounters. The dataset contains demographic attributes and health-related fields, including race, age bands, diagnoses, medication statuses, and readmission outcome. It includes sensitive demographic information, even though it is a public research dataset. Keep the files local and do not publish patient-level output.

**Date lesson:** the CSV does not contain an admission or discharge date. `time_in_hospital` is a length in days, not a date. This pipeline therefore does not invent encounter dates or attempt date parsing. In a real EHR pipeline, use the actual timestamp field and document its timezone and meaning.

Dataset source and citation: [UCI Machine Learning Repository — Diabetes 130-US Hospitals for Years 1999–2008](https://archive.ics.uci.edu/dataset/296/diabetes%2B130-us%2Bhospitals%2Bfor%2Byears%2B1999-2008), DOI: 10.24432/C5230J. The dataset is licensed CC BY 4.0; retain attribution if you share adaptations.

## 1. Project files

The practice expects this structure:

```text
pipeline_practice/
├── data/
│   ├── raw/
│   │   ├── diabetic_data.csv
│   │   └── IDS_mapping.csv
│   └── processed/       # created by the pipeline
├── ehr_pipeline.py
└── EHR_Pipeline_Practice_Guide.md
```

The raw files are inputs. Do not edit them; the pipeline writes new files under `data\processed`.

## 2. Set up the environment

Open PowerShell and run:

```powershell
cd S:\AI_Projects\pipeline_practice
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install pandas pyarrow
```

If PowerShell prevents virtual-environment activation, use `\.venv\Scripts\python.exe` instead of `python` in the commands below.

## 3. Run the pipeline

The file `ehr_pipeline.py` beside this guide contains the complete example. Run:

```powershell
python .\ehr_pipeline.py
```

It should create:

```text
data\processed\ehr_encounters.parquet
data\processed\quality_report.json
```

The terminal reports input rows, exact duplicates removed, remaining duplicate encounter IDs, missing values in key fields, and the output location. It intentionally does not print patient identifiers or individual patient records.

## 4. Inspect the Parquet output

Create `inspect_ehr.py` in the project folder:

```python
from pathlib import Path
import pandas as pd

path = Path("data/processed/ehr_encounters.parquet")
df = pd.read_parquet(path)

print("Rows:", len(df))
print("Columns:", list(df.columns))
print("Admission type counts:")
print(df["admission_type"].value_counts(dropna=False).head(10))
print("Readmission outcome counts:")
print(df["readmitted"].value_counts(dropna=False))
print("Medication count summary:")
print(df["medication_count_known"].describe())
```

Run it with `python .\inspect_ehr.py`. This prints aggregate summaries, not patient-level details.

## 5. What the pipeline teaches

| Stage | Example in this project | Why it matters |
|---|---|---|
| Read | Load the two CSV files as text | Avoid accidental type inference changing codes or IDs |
| Clean | Standardize headers and convert `?`/blank placeholders to missing values | Missingness becomes explicit and consistent |
| Check | Count exact duplicates and repeated encounter IDs | Encounter IDs should identify individual visits |
| Enrich | Decode admission IDs and calculate medication counts | Lookup files add meaning; simple derived fields support analysis |
| Save | Write Parquet and a JSON quality report | Parquet preserves column types; the report makes pipeline behavior reviewable |

## 6. Important data-handling decisions

- **Do not remove repeated patient IDs.** They can represent separate hospital visits. The unique encounter key is `encounter_id`.
- **Exact duplicates:** the script removes rows that are identical across all columns and reports how many were removed.
- **Repeated encounter IDs:** after exact duplicates are removed, the script reports remaining repeated encounter IDs and stops. It does not silently choose which conflicting record is correct.
- **Missing values:** `?` and blank cells become missing. Text such as `None` in lab-result categories is retained as a dataset category meaning a test was not measured; it is not automatically treated as a null.
- **Medication count:** counts medication columns whose status is not `No`, where a status is present. The companion `medication_count_known` shows how many medication fields had a recorded status, so missing statuses are not confused with `No`.
- **Readmission label:** `readmitted_within_30_days` is a historical label derived from `readmitted == <30`. It is included to practice data transformation; this pipeline does not train or assess a prediction model.
- **Identifiers:** encounter and patient numbers are kept as strings to preserve their identity format. Do not include these identifiers in public reports.
- **Mappings:** the mapping file decodes three admission/discharge/source IDs into extra descriptive columns while retaining the original code columns.

## 7. Practice improvements

Once the first run makes sense, try one change at a time:

1. Add checks that `time_in_hospital`, `num_lab_procedures`, and `num_medications` are non-negative.
2. Add a report of missing-value percentages for every column.
3. Add a check that every non-missing admission code has a mapping description.
4. Add a `--input-dir` command-line option so the raw folder can be changed without editing the code.
5. Add a small synthetic CSV with deliberately bad rows and confirm that your checks catch them.

Before adapting this pipeline to real clinical systems, get the required privacy, security, governance, and clinical review. Public research data is not a substitute for the controls required for real patient records.
