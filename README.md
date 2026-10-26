# Healthcare Accessibility ML

Explainable ML for Healthcare Accessibility Assessment and Underserved-District
Identification in India — M.Tech Advanced Machine Learning course project.

## Team
- Kshitiz Reddy (A26MTAI0008) — data collection & integration
- Yashovardhan Kushwaha (A26MTAI0005) — index & modeling
- M Pranit Kumar (A26MTAI0012) — explainability, visualization & writeup

## Current status

**Full national dataset complete.** `processed/national_all_years_merged.csv`
2,166 district-year rows. State-year facility totals were checked
against the RHS report's own totals where available. 87.9% of
district-year rows have population data; the remainder lack a clean
Census 2011 population match, often due to post-2011 districts or
district splits.

**`processed/national_t_to_tplus1.csv`** — the national temporal
(t → t+1) pairs table, 1,267 district pairs across both year-transitions,
ready to feed Yashovardhan's modeling pipeline at full scale.

**D-HAI modeling — first national-scale-ready result.** Yashovardhan's
tuned Random Forest (trained on the original 5-state pilot) hit
Accuracy 0.970 / F1 0.946 / ROC-AUC 0.993, with SHAP + permutation
importance + error analysis + a facility-only ablation. Underserved
label: D-HAI ≤ 0.2115131448 (threshold computed from the training-year
distribution only, to avoid leakage). PR merged to `main`. Next step is
rerunning this on the full national pairs table.

See `DATA_SOURCES.md` for full methodology, source catalog, crosswalk
decisions, and known limitations/anomalies (section 10 covers a confirmed
anomaly in the *official* RHS 2020-21 report for several Jharkhand
districts — not a transcription error on our end).

**Open decisions for the team:**
1. How to handle the ~15% of districts nationwide with no 2011
   population match (exclude, or source an alternate population figure).
2. Whether to stick with Census 2011 or consider the modern population
   alternative documented in `DATA_SOURCES.md` (not yet adopted, since
   switching would affect the D-HAI formula).

**In progress:** Yashovardhan validating D-HAI at national scale; Pranit
building EDA/visualization against the full dataset.

## Folder structure
- `raw/` — untouched source files as downloaded (RHS PDFs, population data,
  LGD codes). Never edit files in here directly — always copy before
  cleaning.
- `processed/` — cleaned, merged district-year tables. Key files:
  `national_all_years_merged.csv` (the full dataset) and
  `national_t_to_tplus1.csv` (temporal pairs for modeling). Per-batch and
  per-year intermediate files are kept for history/auditing.
- `scripts/` — reusable pipeline code (`merge_pipeline.py`).
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
