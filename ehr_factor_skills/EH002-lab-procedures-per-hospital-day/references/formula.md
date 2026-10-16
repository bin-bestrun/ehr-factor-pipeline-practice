# Formula reference: EH002

- **Name:** Lab Procedures per Hospital Day
- **Output column:** `lab_procedures_per_day`
- **Formula:** `num_lab_procedures / time_in_hospital when time_in_hospital > 0`
- **Unit:** procedures per day
- **Required input columns:** `num_lab_procedures`, `time_in_hospital`
- **Missing values:** invalid or missing numeric values produce a missing output. No value is clinically imputed.

The implementation in `scripts/factor.py` is intended to match the corresponding calculation in `ehr_factor_pipeline.py`.
