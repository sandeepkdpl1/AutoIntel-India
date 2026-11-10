# Phase 2 Data Audit

| Table | Rows | Source file | Purpose |
|---|---:|---|---|
| forecast_monthly | 2769 | ml_forecasting_historical_monthly_series.csv | Monthly estimated model-level volume |
| dashboard_estimates | 2240 | market_dashboard_brand_popularity_registrations.csv | Aggregated estimated manufacturer/body/fuel volume |
| car_specs | 53 | ai_car_assistant_verified_specifications.csv | One current specifications row per brand-model |

The 2769-row master file is retained under `data/raw/master_estimates.csv` for traceability, not imported as a duplicate registration table.

**Checks performed:** no duplicate expected keys in three imported datasets; forecast and dashboard total estimated registrations match master total. This proves internal consistency only.

**Caveats:** Counts are estimates, not official VAHAN or OEM sales. Specification verification has not been independently performed. Prices are dated and variant-dependent. 2026 is partial. Forecasting needs chronological evaluation; avoid reporting accuracy before training/testing. Dealer regional analysis needs separately verified geographic data.
