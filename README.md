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

### Modelling: pilot complete, national pending (owner: Yashovardhan)

The tuned Random Forest on the 5-state pilot reached Accuracy 0.970 / F1 0.946 / ROC-AUC 0.993, with SHAP, permutation importance, error analysis and a facility-only ablation. National D-HAI labels and model evaluation on the 618-unit panel are not done yet.

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
- `notebooks/` — EDA, modeling, and SHAP analysis notebooks (includes
  `d_hai_v1.ipynb`).
- `DATA_SOURCES.md` — full source catalog, join methodology, crosswalk
  decisions, and known limitations/anomalies. Read this before touching
  the data.

## Core join key
District identity is matched using LGD (Local Government Directory) codes,
not district names, since names are inconsistent across sources and years.
State names must also match LGD's exact spelling (e.g. "Jammu And Kashmir",
not "Jammu & Kashmir") — a mismatch silently drops the whole state. See
`DATA_SOURCES.md` for real examples of silent errors this caught.
