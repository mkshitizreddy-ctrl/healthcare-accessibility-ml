# Healthcare Accessibility ML

Explainable ML for Healthcare Accessibility Assessment and Underserved-District
Identification in India — M.Tech Advanced Machine Learning course project.

## Team
- Kshitiz Reddy (A26MTAI0008) — data collection & integration
- Yashovardhan Kushwaha (A26MTAI0005) — index & modeling
- M Pranit Kumar (A26MTAI0012) — explainability, visualization & writeup

## Folder structure
- `raw/` — untouched source files as downloaded (RHS PDFs, population data, LGD codes).
  Never edit files in here directly — always copy before cleaning.
- `processed/` — cleaned, merged district-year tables derived from raw/.
- `notebooks/` — EDA, modeling, and SHAP analysis notebooks.

## Current stage
Running a small pilot first: 5 states (Maharashtra, Uttar Pradesh, Karnataka,
Tamil Nadu, Rajasthan) x 3 years (RHS 2019-20, 2020-21, 2021-22) before scaling
to the full dataset. See project notes for the full pilot checklist.

## Core join key
District identity is matched using LGD (Local Government Directory) codes,
not district names, since names are inconsistent across sources and years.
