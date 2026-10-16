# EHR factor pipeline practice

A beginner-friendly Python project that turns a public hospital-encounter research dataset into cleaned Parquet data, descriptive factor features, reusable factor folders, and a local Streamlit dashboard.

**Learning project only:** the factors are descriptive examples. They are not validated clinical scores, diagnosis tools, treatment recommendations, or patient-risk assessments.

## Project flow

```text
UCI CSV files → ehr_pipeline.py → cleaned encounter Parquet
                → ehr_factor_pipeline.py → factor values + catalog
                → build_ehr_factor_package.py → reusable factor folders
                → app.py → local aggregate dashboard
```

## Dataset setup

The raw dataset is not included in this repository. Download these two files from the [UCI dataset page](https://archive.ics.uci.edu/dataset/296/diabetes%2B130-us%2Bhospitals%2Bfor%2Byears%2B1999-2008) and place them here:

```text
data/raw/diabetic_data.csv
data/raw/IDS_mapping.csv
```

UCI identifies the dataset as **Diabetes 130-US Hospitals for Years 1999–2008**, DOI [10.24432/C5230J](https://doi.org/10.24432/C5230J), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The dataset page notes that records include sensitive demographic attributes such as age, gender, and race. This repository ignores raw CSVs and generated encounter-level outputs by default. If you choose to redistribute the dataset, include the required attribution and review the source license and data handling implications.

## Run locally on Windows

Open PowerShell in this project folder. Create your own virtual environment; do not copy another computer's `.venv` folder.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Download/place the two CSV files as described above, then run each stage in order:

```powershell
python .\ehr_pipeline.py
python .\ehr_factor_pipeline.py
python .\build_ehr_factor_package.py
python -m streamlit run .\app.py
```

Streamlit prints the local address, usually `http://localhost:8501`. Stop the app with `Ctrl+C` in the PowerShell window.

If PowerShell prevents environment activation, run the scripts with the environment's Python directly:

```powershell
.\.venv\Scripts\python.exe .\ehr_pipeline.py
.\.venv\Scripts\python.exe .\ehr_factor_pipeline.py
.\.venv\Scripts\python.exe .\build_ehr_factor_package.py
.\.venv\Scripts\python.exe -m streamlit run .\app.py
```

## What each script does

- `ehr_pipeline.py`: standardizes CSV columns/values, handles exact duplicates, checks encounter IDs, decodes admission lookup codes, calculates ETL fields, and writes `data/processed/ehr_encounters.parquet` plus `quality_report.json`.
- `ehr_factor_pipeline.py`: calculates five descriptive encounter-level factors and writes `ehr_factor_values.parquet` plus `ehr_factor_catalog.json`.
- `build_ehr_factor_package.py`: reads the factor definitions and creates `ehr_factor_skills/`, including one `SKILL.md`, `scripts/factor.py`, and formula reference per stable ID.
- `app.py`: displays aggregate factor distributions, missing-value counts, and summary statistics. It does not show encounter-level rows or identifiers.
- `EHR_Factor_Project_Learning_Guide.md`: explains the project, formulas, assumptions, troubleshooting, and learning exercises.
- `EHR_Pipeline_Practice_Guide.md`: introduces the earlier generic CSV-to-Parquet practice.

Generated Parquet and report files go under `data/processed/` and are ignored by Git. The factor package is included as reusable project material; regenerate it after changing definitions.

## Adding a factor

1. Add a stable ID and metadata entry in `FACTOR_DEFINITIONS` in `ehr_factor_pipeline.py`.
2. Add its calculation to `generate_factors()`.
3. Add the corresponding implementation template and required input fields in `build_ehr_factor_package.py`.
4. Rerun the factor pipeline and package builder.
5. Inspect missing values, units, and edge cases before using the dashboard.

## Limitations and data handling

The dataset does not include encounter admission/discharge dates; `time_in_hospital` is a duration in days. The pipeline does not invent dates. Multiple rows per patient can represent separate encounters. Do not use this project for real patient care or operational decisions, and do not commit real EHR data, credentials, or patient-level extracts.

The dataset is CC BY 4.0; that license does not automatically license this project's code. Add a separate code license if you want to grant others permission to reuse or modify the code.
