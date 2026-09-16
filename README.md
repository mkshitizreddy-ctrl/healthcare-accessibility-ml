# Healthcare Accessibility ML

Explainable ML for Healthcare Accessibility Assessment and Underserved-District
Identification in India — M.Tech Advanced Machine Learning course project.

## Team
- Kshitiz Reddy (A26MTAI0008) — data collection & integration
- Yashovardhan Kushwaha (A26MTAI0005) — index & modeling
- M Pranit Kumar (A26MTAI0012) — explainability, visualization & writeup

## Current status

**Pilot complete and verified.** Built and tested the full data pipeline
(RHS facility data → LGD district codes → Census population) on 5 states
(Karnataka, Maharashtra, Rajasthan, Tamil Nadu, Uttar Pradesh) across 3
years (2019-20 to 2021-22): 629 clean district-year rows, 95.5% population
coverage, every gap explained. See `DATA_SOURCES.md` for the full
methodology, source list, and known limitations.

The merge pipeline has been generalized (`scripts/merge_pipeline.py`) and
is ready to scale to the full nationwide dataset. A national audit of the
LGD/Census files (ahead of scaling) found:
- A leading-zero code-formatting bug affecting 99 districts nationwide —
  already fixed in the pipeline.
- ~16% of districts nationwide (125 of 785) are post-2011 creations with
  no Census 2011 population match — bigger than the pilot suggested (4.3%),
  worth a team decision before full-scale build.
- Census 2011 population is 15 years stale, and no official nationwide
  district-level population projection exists. One modelled alternative
  (WorldPop-based 2020 district estimates) was found but not adopted —
  flagged for team discussion since it would affect the D-HAI formula.

**Since then (solo prep while team works on D-HAI/EDA):**
- Resolved the NHP question — dropped from scope (state-level only, no
  usable district-wise tables).
- Checked RHS Section VI (bed counts) — also state-level only; no
  additional district-level RHS tables exist beyond Section II.
- Extended the pipeline to Kerala, West Bengal, Gujarat (2021-22): 70/70
  rows matched to LGD, 84.3% population coverage, one new crosswalk entry
  (Dohad→Dahod). Confirms the pipeline generalizes beyond the original 5
  states.

**Open decisions for the team:**
1. How to handle the ~16% of districts with no 2011 population match at
   full scale (exclude them, or find an alternate source).
2. Whether to stick with Census 2011 or consider the modern population
   alternative documented in `DATA_SOURCES.md`.

**In progress:** Yashovardhan drafting D-HAI v1 against the pilot dataset;
Pranit building an initial EDA notebook.

## Folder structure
- `raw/` — untouched source files as downloaded (RHS PDFs, population data,
  LGD codes). Never edit files in here directly — always copy before
  cleaning.
- `processed/` — cleaned, merged district-year tables derived from raw/.
  Includes the pilot dataset (`pilot_merged.csv`) and its match-review file
  (`pilot_merged.review.csv`).
- `scripts/` — reusable pipeline code (`merge_pipeline.py`).
- `notebooks/` — EDA, modeling, and SHAP analysis notebooks.
- `DATA_SOURCES.md` — full source catalog, join methodology, crosswalk
  decisions, and known limitations. Read this before touching the data.

## Core join key
District identity is matched using LGD (Local Government Directory) codes,
not district names, since names are inconsistent across sources and years
(confirmed necessary — see `DATA_SOURCES.md` for real examples of silent
mismatches this caught).
