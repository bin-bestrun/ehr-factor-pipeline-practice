# Formula reference: EH005

- **Name:** Hospital Stay Days
- **Output column:** `time_in_hospital`
- **Formula:** `time_in_hospital`
- **Unit:** days
- **Required input columns:** `time_in_hospital`
- **Missing values:** invalid or missing numeric values produce a missing output. No value is clinically imputed.

The implementation in `scripts/factor.py` is intended to match the corresponding calculation in `ehr_factor_pipeline.py`.
