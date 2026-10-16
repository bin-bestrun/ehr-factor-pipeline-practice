# Formula reference: EH001

- **Name:** Prior Utilization Count
- **Output column:** `prior_utilization_count`
- **Formula:** `number_outpatient + number_emergency + number_inpatient`
- **Unit:** count
- **Required input columns:** `number_outpatient`, `number_emergency`, `number_inpatient`
- **Missing values:** invalid or missing numeric values produce a missing output. No value is clinically imputed.

The implementation in `scripts/factor.py` is intended to match the corresponding calculation in `ehr_factor_pipeline.py`.
