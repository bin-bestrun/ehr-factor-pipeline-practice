# EHR Factor Project: Beginner Learning Guide

This guide explains the local EHR practice project from raw CSV files through a cleaned Parquet dataset, calculated factors, reusable factor folders, and a Streamlit dashboard.

The purpose is to learn Python data pipeline design. The factor values are descriptive practice features. They are not validated clinical scores, diagnosis tools, treatment recommendations, or patient risk assessments.

## 1. What this project uses

The raw data folder contains:

```text
data/raw/
├── diabetic_data.csv
└── IDS_mapping.csv
```

The files come from the UCI **Diabetes 130-US Hospitals for Years 1999–2008** research dataset. The dataset contains hospital encounters and includes demographic and health-related fields. It is licensed CC BY 4.0; give attribution when sharing adaptations. See the [UCI dataset page](https://archive.ics.uci.edu/dataset/296/diabetes%2B130-us+hospitals+for+years+1999-2008), DOI `10.24432/C5230J`.

The supplied project run produced 101,766 encounter rows and 71,518 unique patients. Multiple encounter rows for the same patient are expected: the row is an encounter, not a unique person.

**Date limitation:** the source does not have an admission date or discharge date column. `time_in_hospital` is a number of days, not a date. The project does not invent dates or claim to provide a chronological patient timeline.

Although this is a public research dataset, it includes demographic and health-related information. Keep the practice local, avoid publishing patient-level records or identifiers, and never substitute real patient records into this beginner project without proper authorization and safeguards.

## 2. Project map

```text
pipeline_practice/
├── data/
│   ├── raw/
│   │   ├── diabetic_data.csv
│   │   └── IDS_mapping.csv
│   └── processed/
│       ├── ehr_encounters.parquet
│       ├── quality_report.json
│       ├── ehr_factor_values.parquet
│       └── ehr_factor_catalog.json
├── ehr_pipeline.py
├── ehr_factor_pipeline.py
├── build_ehr_factor_package.py
├── ehr_factor_skills/
│   ├── README.md
│   ├── factor_index.json
│   └── EH###-factor-name/
│       ├── SKILL.md
│       ├── scripts/factor.py
│       └── references/formula.md
├── app.py
└── EHR_Factor_Project_Learning_Guide.md
```

The `data/raw` files are the inputs. The scripts write new results to `data/processed`; they do not need to edit the raw CSVs.

## 3. How the parts connect

```text
Two raw CSV files
       │
       ▼
 ehr_pipeline.py
       ├── cleans and checks encounters
       ├── decodes admission ID fields
       └── writes ehr_encounters.parquet + quality_report.json
       │
       ├───────────────┐
       ▼               ▼
 ehr_factor_pipeline.py   build_ehr_factor_package.py
 ├── calculates values   ├── reads definitions from the factor pipeline
 └── writes factor       └── writes one reusable folder per factor
     Parquet + catalog              │
       └───────────────┬─────────────┘
                       ▼
                     app.py
            local aggregate dashboard
```

The first two scripts create the processed data. The package builder creates reusable factor code and documentation. The dashboard reads the factor-value Parquet and package index to let you explore aggregate distributions.

## 4. Set up and run the project

On Windows, install Python 3.11 or newer. Open PowerShell in the folder where you extracted this project and create a project-local environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell prevents activation, call `.\.venv\Scripts\python.exe` instead of `python` in the commands below.

Download the two UCI CSV files as described in the project README and place them in `data\raw`. Then run the stages in order:

```powershell
python .\ehr_pipeline.py
python .\ehr_factor_pipeline.py
python .\build_ehr_factor_package.py
```

Start the local dashboard:

```powershell
python -m streamlit run .\app.py
```

Streamlit prints a local address, usually `http://localhost:8501`. Stop it from the PowerShell window with `Ctrl+C`.
## 5. Stage one: clean encounters with `ehr_pipeline.py`

### Reading the raw files

The script reads the encounter CSV as text first. That is deliberate: encounter and patient identifiers are identifiers, not quantities to perform arithmetic on. Keeping them as strings helps preserve their identity.

### Standardizing missing values

The dataset uses `?` as a missing-value marker. The script converts `?` and empty cells to pandas missing values. It keeps the literal text `None` in fields such as test-result categories, because in that context the source uses it to mean a test was not measured.

### Checking duplicates and IDs

The script removes exact duplicate rows and records how many were removed. Then it checks that `encounter_id` is present and unique. If conflicting rows share an encounter ID, it stops and asks for an explicit resolution rather than silently choosing one.

Repeated `patient_nbr` values are allowed. A person can have more than one hospital visit, so dropping repeated patients would discard encounters.

### Decoding mapping IDs

`IDS_mapping.csv` contains lookup sections for admission type, discharge disposition, and admission source. The pipeline retains the source ID columns and adds human-readable descriptive columns.

### Derived encounter fields

The ETL script creates `medication_count` and `medication_count_known` from the medication status fields. A status other than `No` is counted in the first field when it is recorded; a missing status is not treated as `No`.

It also creates `readmitted_within_30_days` as a historical label from the source's `readmitted` value. That outcome is not used as one of the factors and is omitted from the factor output.

### Outputs

- `data/processed/ehr_encounters.parquet`: cleaned encounter data, mapping labels, and derived ETL fields.
- `data/processed/quality_report.json`: counts, missing-value totals, and mapping coverage.

Parquet is a compact columnar file format that preserves types more reliably than CSV.

## 6. Stage two: calculate factors with `ehr_factor_pipeline.py`

The factor pipeline reads `ehr_encounters.parquet`, creates one numeric value per factor for each encounter, and writes:

- `data/processed/ehr_factor_values.parquet`
- `data/processed/ehr_factor_catalog.json`

The catalog keeps each stable factor ID, human-readable name, output column, formula, description, and unit together.

### The five practice factors

| ID | Name | Output column | Formula / meaning |
|---|---|---|---|
| EH001 | Prior Utilization Count | `prior_utilization_count` | `number_outpatient + number_emergency + number_inpatient`; remains missing when all three inputs are missing |
| EH002 | Lab Procedures per Hospital Day | `lab_procedures_per_day` | `num_lab_procedures / time_in_hospital`, only when hospital days are greater than zero |
| EH003 | Procedures per Hospital Day | `procedures_per_day` | `num_procedures / time_in_hospital`, only when hospital days are greater than zero |
| EH004 | Recorded Medication Count | `medication_count` | Reuses the medication count created by the ETL pipeline |
| EH005 | Hospital Stay Days | `time_in_hospital` | Source-reported stay duration in days; it is not a calendar date |

The word **factor** here means a calculated data feature. It does not mean a proven cause, clinical risk, or treatment effect.

## 7. Stage three: make reusable folders with `build_ehr_factor_package.py`

The package builder imports `FACTOR_DEFINITIONS` from `ehr_factor_pipeline.py`. For each factor, it creates a folder similar to:

```text
EH001-prior-utilization-count/
├── SKILL.md
├── scripts/factor.py
└── references/formula.md
```

The package root also contains `factor_index.json` and `README.md`.

- `EH001` is the stable ID. Keep it the same when you clarify wording; use a new ID for a genuinely different factor.
- `SKILL.md` tells a person or agent what the factor does and what columns it expects.
- `scripts/factor.py` contains `compute_factor(df)`, which returns a pandas Series aligned with the input rows.
- `references/formula.md` records the equation, units, required columns, and missing-value behavior.
- `factor_index.json` provides a machine-readable catalog for apps and other tools.

If you change a factor definition, update its computation template in `build_ehr_factor_package.py` as well. This keeps the reusable `factor.py` calculation aligned with the pipeline calculation. The builder refuses to refresh an existing package index unless you pass `--overwrite`:

```powershell
python .\build_ehr_factor_package.py --overwrite
```

That option refreshes generated files and does not delete unrelated files in the output folder.

## 8. Stage four: explore factors with `app.py`

The local Streamlit dashboard reads:

- `data/processed/ehr_factor_values.parquet`
- `ehr_factor_skills/factor_index.json`

Choose a factor in the sidebar to see its aggregate value distribution, missing-value count, summary statistics, and formula. The **Compare all factors** section shows aggregate availability and summary values across the factors.

The dashboard deliberately does not list encounter IDs or patient-level rows. It is designed for local learning and descriptive exploration, not clinical interpretation. Since these features have different units and meanings, do not compare their numeric magnitudes as if they were on the same scale.

## 9. How to create a new practice factor

Use this sequence when adding a factor:

1. Write the idea in plain English. Be precise about whether it describes an encounter or a patient.
2. Confirm each required input column exists and understand its source definition.
3. Write the formula, unit, and missing/zero-denominator behavior before coding.
4. Add its stable ID and metadata to `FACTOR_DEFINITIONS` in `ehr_factor_pipeline.py`.
5. Add the actual calculation to `generate_factors()` in that file.
6. Add the matching code template and required-input definition to `build_ehr_factor_package.py`.
7. Re-run the factor pipeline and package builder.
8. Inspect the new values, missingness, and edge cases before relying on them.
9. Confirm the dashboard includes the new column from the package index.

When checking a new formula, inspect a few rows you understand and check edge cases: missing inputs, zero hospital days, and unusual values. Compare the standalone folder's `compute_factor(df)` output with the matching column from `ehr_factor_pipeline.py` on the same rows.

## 10. Common problems

### The input file cannot be found

Confirm the raw files are in `data\raw` and run PowerShell from the project folder. The scripts build paths relative to their own file location, so you can also run them from another current directory using the full script path.

### A required column is missing

The pipeline or factor script lists the expected columns in its error. Check the CSV header and the normalization rules; do not silently rename a different field unless it has the same meaning.

### Repeated encounter ID error

The pipeline removes exact duplicate rows first. If the same encounter ID remains on conflicting rows, inspect the source and decide how to resolve it. Do not drop them arbitrarily.

### Dashboard says factor files are missing

Run the ETL, factor calculation, and package builder in order. Confirm that both `ehr_factor_values.parquet` and `ehr_factor_skills\factor_index.json` exist.

### The package already exists

Use `--overwrite` only when you want to regenerate the builder's output. Keep your own notes or custom files in the package folder; the builder does not delete unrelated files.

### A Python package is missing

Use the same interpreter that runs the dashboard:

```powershell
python -m pip install -r requirements.txt
```

## 11. Suggested learning exercises

1. Print only aggregate counts from `quality_report.json`; explain what each count tells you.
2. Manually calculate EH001 for a few sample rows and compare with the saved factor column.
3. Find rows where `time_in_hospital` is missing or zero and verify the daily-rate factors are missing rather than infinite.
4. Add a factor such as `num_medications / time_in_hospital`, with a clear name and explicit handling for zero days.
5. Add a factor definition and folder, then confirm the dashboard discovers it.
6. Create a tiny synthetic CSV with a `?` value and a duplicate encounter, and observe how the pipeline responds.
7. Save a short note explaining one assumption that could change if you used a different dataset.

## 12. Key ideas to remember

- The pipeline makes data handling consistent; factor code makes each formula explicit; the package makes factors reusable; the app makes aggregate results easier to explore.
- A stable ID connects each factor's formula, code, metadata, and display name.
- A readable name does not prove a feature is meaningful. Check definitions, units, missingness, and edge cases.
- This historical public dataset is for practice. The project is not a clinical system and must not be used to make decisions about real patients.


