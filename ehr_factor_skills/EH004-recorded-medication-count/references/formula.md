# Formula reference: EH004

- **Name:** Recorded Medication Count
- **Output column:** `medication_count`
- **Formula:** `count medication fields with a recorded status other than No`
- **Unit:** count
- **Required input columns:** `medication_count`
- **Missing values:** invalid or missing numeric values produce a missing output. No value is clinically imputed.

The implementation in `scripts/factor.py` is intended to match the corresponding calculation in `ehr_factor_pipeline.py`.
