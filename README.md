# Healthcare Accessibility ML

Explainable ML for Healthcare Accessibility Assessment and Underserved-District
Identification in India — M.Tech Advanced Machine Learning course project.

## Team
- Kshitiz Reddy (A26MTAI0008) — data collection & integration
- Yashovardhan Kushwaha (A26MTAI0005) — index & modeling
- M Pranit Kumar (A26MTAI0012) — explainability, visualization & writeup

## Current status

### Data pipeline: complete (national, all states and UTs, 2019-20 to 2021-22)

| File | Rows | What it is |
|---|---:|---|
| `processed/national_all_years_merged.csv` | 2,178 | District-year RHS facility counts joined to LGD and Census 2011. Includes Sikkim, added 2026-10-30. |
| `processed/national_all_years_2011units.csv` | 1,854 | **Modelling panel.** 618 Census-2011 boundary units × 3 years, 100% population coverage, `*_per_100k` features, quality flags. |
| `processed/national_t_to_tplus1_2011units.csv` | 1,236 | **Temporal t → t+1 pairs** on the same 618 units. |
| `processed/unit_population_2020.csv` | 618 | Harvard 2020 modelled population per unit. For sensitivity analysis only. |
| `processed/unit_membership.csv` | 640 | Unit → member Census-2011 districts. |

- **Why units instead of districts:** districts created after 2011 have no 2011 population, and their parent districts' per-capita values are biased downward. Re-aggregating to 2011 boundaries fixes both problems. See `DATA_SOURCES.md` §11.
- **Validation:** `scripts/audit_rhs_totals.py` reconciles every multi-district state-year against the RHS report's own "Total Districts" line. All 102 match (§14).
- **Flags:**
  - `is_urban_unit`: 10 metro units where RHS rural counts are about 0 by definition.
  - `known_anomaly`: 8 unit-years with documented source anomalies.
  - `pop2020_plausible`: 34 units whose 2020 estimates are likely misallocated by the source's boundary files.

  Flags mark rows; nothing is dropped (§12–13).
- The older district-level files `processed/national_t_to_tplus1.csv` (1,267 pairs) and the copies of `national_all_years_merged.csv` at the repo root and in `clean_dataset/` are **superseded**. Use the `*_2011units.csv` files.

### Modelling: national results complete (owner: Yashovardhan, PR #9)

**D-HAI (national).** The five `*_per_100k` facility rates are min-max normalised using **2019-20 (baseline year) parameters only** and averaged with equal weights. A unit is labelled *underserved* when its D-HAI ≤ the baseline-year 25th percentile (0.0312). Urban units (30 rows) and known-anomaly unit-years (8 rows) are excluded, leaving 1,816 of 1,854 records. Outputs: `processed/national_dhai_results.csv` and `processed/national_dhai_metadata.json`.

**Task.** Predict whether a unit will be underserved in year t+1 from its five facility rates in year t.
- Train: 2019-20 → 2020-21 (600 units)
- Test: 2020-21 → 2021-22 (601 units, 142 underserved)

Hyperparameters were tuned by cross-validation on the training period only (`results/national_best_parameters.json`).

| Model (test set) | Accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|
| Random Forest | 0.972 | 0.925 | 0.958 | 0.941 | 0.992 | 0.971 |
| Logistic Regression | 0.962 | 0.922 | 0.915 | 0.919 | 0.990 | 0.963 |
| Decision Tree | 0.948 | 0.849 | 0.951 | 0.897 | 0.976 | 0.918 |
| Persistence baseline (label at t) | 0.972 | 0.931 | 0.951 | 0.941 | 0.964 | 0.897 |

**How to read this.**
- **Labels:** Random Forest **matches** the persistence baseline when predicting the labels themselves (F1 0.9412 vs 0.9408).
- **Ranking:** it is clearly better at ranking units by risk (ROC-AUC 0.992 vs 0.964, PR-AUC 0.971 vs 0.897). The persistence baseline only produces 0/1 scores, so its ROC-AUC and PR-AUC have a single operating point and limited resolution. The gap partly reflects that RF outputs a continuous probability.
- **Why the labels are so persistent:** population is fixed at Census 2011, so year-to-year changes in the features come only from facility counts, which change little. The model's main added value is the probability ranking, not the hard labels.

**Explainability and robustness**
- **SHAP (mean |SHAP|).** The most important feature is sub-centres per 100k (0.172), followed by PHCs (0.105), sub-divisional hospitals (0.071), CHCs (0.054) and district hospitals (0.019). Files: `results/shap_*`.
- **Errors.** 17 of 601 test units were misclassified (11 false positives, 6 false negatives). Listed in `results/national_misclassified_units.csv`.
- **Threshold sensitivity.** At the 20th, 25th and 30th percentiles, Random Forest F1 is 0.898, 0.941 and 0.943 (`results/threshold_sensitivity_results.csv`).
- **Anomaly sensitivity.** Keeping the 8 anomalous unit-years changes F1 from 0.941 to 0.943 (`results/anomaly_sensitivity_results.csv`).
- **Reproducibility.** `python reproduce_predictions.py` reloads `models/random_forest.joblib` and regenerates the test predictions.

Pipeline scripts, in order: `national_dhai.py` → `validate_national_dhai.py` → `prepare_temporal_dataset.py` → `validate_temporal_split.py` → `train_temporal_models.py` → `evaluate_persistence_baseline.py` → `final_evaluation.py` → `shap_explainability.py` → `error_analysis.py` → `threshold_sensitivity.py` / `anomaly_sensitivity.py`.

Not done yet: a robustness check using the Harvard 2020 population (`processed/unit_population_2020.csv`).

### Visualisation / dashboard (owner: Pranit)

`ML_APP.py` is an exploratory facilities dashboard, not a prediction app. It currently reads the root copy of the merged CSV, which does not include Sikkim.

## Reproducing the data pipeline

```bash
pip install -r requirements.txt          # pdftotext (poppler-utils) is also needed for the audit
# Put the three RHS PDFs in raw/rhs/ (see "Source files" below)
python scripts/reaggregate_2011_units.py # -> *_2011units.csv, unit_membership.csv
python scripts/add_population_2020.py    # -> unit_population_2020.csv
python scripts/audit_rhs_totals.py --pdf 2019-20=raw/rhs/RHS_2019-20.pdf \
    --pdf 2020-21=raw/rhs/RHS_2020-21.pdf --pdf 2021-22=raw/rhs/RHS_2021-22.pdf
```

Expected output: `618 units`, `pairs : 1236`, `ALL RECONCILED`.

## Source files not in git

The RHS PDFs are excluded by `.gitignore` (`*.pdf`; up to 30 MB each). Obtain them from the Ministry of Health & Family Welfare, Statistics Division ("Rural Health Statistics" publications on mohfw.gov.in). A public mirror is in the PARI library (ruralindiaonline.org). Save them under these exact names and verify the checksums:

| File | Report (data as on) | MD5 | District tables (PDF pages) |
|---|---|---|---|
| `raw/rhs/RHS_2019-20.pdf` | RHS 2019-20 (31 Mar 2020) | `3cf1d35d183e922615c568fea340ee13` | 132–147 |
| `raw/rhs/RHS_2020-21.pdf` | RHS 2020-21 (31 Mar 2021) | `9a2b3e5d2b127c6f05ce0bb9a036b985` | 116–131 |
| `raw/rhs/RHS_2021-22.pdf` | RHS 2021-22 (31 Mar 2022) | `8acdf0937c0800f1dcb4dc62014b30a8` | 114–129 |

Check them with `certutil -hashfile <file> MD5` on Windows or `md5sum <file>` on Linux and macOS. All other raw inputs (LGD, Census 2011, lineage, the Harvard 2020 xlsx) are committed.

## Folder structure
- `raw/` — untouched source files as downloaded (RHS PDFs, population data,
  LGD codes). Never edit files in here directly — always copy before
  cleaning.
- `processed/` — cleaned and merged tables. Key files:
  `national_all_years_2011units.csv` (modelling panel),
  `national_t_to_tplus1_2011units.csv` (temporal pairs) and
  `national_all_years_merged.csv` (district-level source). Per-batch and
  per-year intermediate files are kept for history and auditing.
- `scripts/` — pipeline code: `merge_pipeline.py` (RHS → LGD → Census join),
  `reaggregate_2011_units.py`, `add_population_2020.py`, `audit_rhs_totals.py`.
  Modelling: `national_dhai.py`, `train_temporal_models.py`, `final_evaluation.py`,
  `shap_explainability.py` and related scripts (see Modelling above).
- `notebooks/` — pilot (`d_hai_v1.ipynb`) and national
  (`national_dhai_analysis.ipynb`) analysis notebooks.
- `models/` — trained model (`random_forest.joblib`).
- `results/` — national evaluation tables, predictions, SHAP outputs and figures.
- `DATA_SOURCES.md` — full source catalog, join methodology, crosswalk
  decisions, and known limitations/anomalies. Read this before touching
  the data.

## Core join key
District identity is matched using LGD (Local Government Directory) codes,
not district names, since names are inconsistent across sources and years.
State names must also match LGD's exact spelling (e.g. "Jammu And Kashmir",
not "Jammu & Kashmir") — a mismatch silently drops the whole state. See
`DATA_SOURCES.md` for real examples of silent errors this caught.
