# Data Sources & Methodology Notes

This documents where every piece of the pilot dataset came from, the decisions
made while joining it together, and the known limitations — written while
still fresh, for reuse in the final report.

## 1. Source Catalog

| File | Source | Retrieved via | Notes |
|---|---|---|---|
| `raw/rhs/RHS_2019-20.pdf` | Ministry of Health & Family Welfare, Rural Health Statistics 2019-20 | ruralindiaonline.org (PARI library mirror) | Scanned PDF, no text layer on the direct print-to-PDF copy |
| `raw/rhs/RHS_2020-21.pdf` | Ministry of Health & Family Welfare, Rural Health Statistics 2020-21 | archive.org (PARI.rural-health-statistics-2020-21), "PDF" download option | Has OCR text layer — Ctrl+F works |
| `raw/rhs/RHS_2021-22.pdf` | Ministry of Health & Family Welfare, Rural Health Statistics 2021-22 | archive.org (PARI.rural-health-statistics-2021-22), "PDF" download option | Has OCR text layer — Ctrl+F works |
| `raw/population/census2011_districts.csv` | Census of India 2011, district-level population | GitHub mirror (nishusharma1608/India-Census-2011-Analysis) | Community-compiled CSV of official Census 2011 figures |
| `raw/lgd/lgd_districts.csv` | Local Government Directory (LGD), Ministry of Panchayati Raj | data.gov.in — official LGD districts resource | Provides the `district_census2011_code` used as the join key |

**Table used from each RHS report:** Section II, "District-wise Health Care
Infrastructure in India" — the only genuinely district-level table (columns:
Sub Centres, PHCs, CHCs, Sub Divisional Hospital, District Hospital). RHS
manpower data (doctors, nurses, health workers) is reported only at
state/UT level via separate "Comparative Statement" tables — not usable as a
true district-level feature.

## 2. Extraction & Verification

RHS district tables were extracted for the 5 pilot states (Karnataka,
Maharashtra, Rajasthan, Tamil Nadu, Uttar Pradesh) across all 3 years.
Every state's extracted row sums were checked against the report's own
"Total Districts = ..." summary line and matched exactly in all 15
state-year combinations (5 states × 3 years) — no transcription errors.

## 3. District Join: RHS → LGD → Population

Districts were matched across sources using **LGD codes**, not district
names, because RHS district names are inconsistent both across years and
against the LGD's official spelling.

**Join process:**
1. Normalize district name text (lowercase, strip punctuation).
2. Try exact match against LGD district names within the same state.
3. Apply a manual crosswalk for known historical renames (below).
4. Fall back to fuzzy string matching only for cosmetic spelling drift
   (accent/spacing differences), reviewed manually.
5. Use the resulting `district_census2011_code` to join Census 2011
   population.

**Important finding:** naive fuzzy matching (no manual review) produced two
silent wrong matches:
- "Faizabad" (old name for Ayodhya, UP) → incorrectly matched to
  "Firozabad" (a real, different UP district)
- "Sant Ravidas Nagar" (old name for Bhadohi, UP) → incorrectly matched to
  "Sant Kabir Nagar" (a real, different UP district)

Both were caught by manually reviewing every non-exact match rather than
trusting the fuzzy-match score alone. **Lesson for scaling up:** every
non-exact match must be manually reviewed before being trusted, especially
for renamed districts, since fuzzy string similarity can be high between
genuinely different places.

### Manual crosswalk (verified against `lgd_districts.csv`)

| RHS name (old) | Correct LGD name | State | Reason |
|---|---|---|---|
| Belgaum | Belagavi | Karnataka | Official renaming |
| Bellary | Ballari | Karnataka | Official renaming |
| Bijapur | Vijayapura | Karnataka | Official renaming |
| Gulbarga | Kalaburagi | Karnataka | Official renaming |
| Mysore | Mysuru | Karnataka | Official renaming |
| Aurangabad | Chhatrapati Sambhajinagar | Maharashtra | Official renaming (2023) |
| Osmanabad | Dharashiv | Maharashtra | Official renaming (2023) |
| Bid | Beed | Maharashtra | Alternate spelling |
| Faizabad | Ayodhya | Uttar Pradesh | Official renaming |
| Allahabad | Prayagraj | Uttar Pradesh | Official renaming |
| C S M Nagar | Amethi | Uttar Pradesh | Official renaming |
| Jyotiba Phule Nagar | Amroha | Uttar Pradesh | Official renaming |
| Kashi Ram Nagar | Kasganj | Uttar Pradesh | Official renaming |
| Lakhimpur Kheri | Kheri | Uttar Pradesh | Alternate/shortened name |
| Maunathbhanjan | Mau | Uttar Pradesh | Alternate/shortened name |
| Sant Ravidas Nagar | Bhadohi | Uttar Pradesh | Official renaming |
| Tuticorin | Thoothukkudi | Tamil Nadu | Official renaming |

## 4. Known Limitations

- **Post-2011 new districts have no Census 2011 population figure.**
  Districts created after the 2011 Census (e.g. Palghar, Chengalpattu,
  Ranipet, Hapur, Sambhal, Shamli, Amethi in some years) carry
  `district_census2011_code = 000` in LGD and cannot be joined to a 2011
  population figure. This affects 27 of the 629 pilot rows (4.3%). These
  districts will need either a modern population estimate from a different
  source or exclusion, decided before the full-scale build.
- **Mumbai / Mumbai Suburban combined-entry mismatch.** In RHS 2019-20,
  Mumbai and Mumbai Suburban are reported as one combined "Brihan Mumbai"
  row, while LGD/Census treat them as two separate districts. This single
  row (1 of 629) could not be cleanly matched or split without further
  work and was left unmatched for the pilot.
- **Manpower data is state-level, not district-level.** RHS reports doctors,
  nurses, and health worker counts only at the state/UT level. Any
  manpower-based feature in the final model will be a state-level value
  applied uniformly to all districts in that state — not a true
  district-level measurement. This should be stated explicitly in the
  final report, not implied to be district-specific.
- **A code-formatting mismatch between LGD and Census files** (LGD stores
  codes with leading zeros, e.g. "099"; Census stores them without, e.g.
  "99") caused one initially-missed join (Ganganagar, Rajasthan) until
  codes were normalized on both sides before joining. Worth checking for
  when scaling to the full nationwide dataset.

## 5. Pilot Test Result

629 district-year rows across 5 states × 3 years, with 95.5% population
coverage. Every gap in the remaining 4.5% is explained by one of the
limitations above — none are unexplained data loss. This clears the pilot's
pass condition from the feasibility note.

## 6. National-Scale Audit (done ahead of full build)

Before scaling beyond the 5 pilot states, the LGD and Census files
(which already cover all of India) were audited directly:

- **Leading-zero code bug: 99 districts nationwide affected**, not just
  Ganganagar. Any LGD code under 100 (mostly Jammu & Kashmir, Ladakh,
  Himachal Pradesh, Punjab, Haryana, Uttarakhand, Delhi) is zero-padded to
  3 digits in the LGD file but stored without padding in the Census file.
  This is already fixed by normalizing codes to integers before joining —
  confirmed to resolve all 99 cases, not just the one found in the pilot.
- **Post-2011 new districts: 125 of 785 nationwide (15.9%)** have no
  Census 2011 population match — much higher than the pilot's 4.3%, because
  the pilot states happened to have few reorganizations. Telangana alone
  has 23 new districts (its 2016 split), Chhattisgarh 15, Andhra Pradesh 13.
  **This needs a decision before the full build**: either source a newer
  population estimate for these ~126 districts, or accept that ~16% of
  districts nationwide will be missing this feature.
- **The rename crosswalk is necessarily incremental** — it can only be
  built as each state's actual RHS district names are seen and compared
  against LGD, since old names aren't predictable in advance. One known
  major rename added as a head start: Madhya Pradesh's Hoshangabad →
  Narmadapuram (2021). Expect more to surface as extraction continues.
- **Census 2011 population is now 15 years stale.** No official
  government district-level population projection exists for all of
  India — the Registrar General only projects at the state level (2020
  report, covering 2011-2036). UNFPA has published district-level
  projections, but only for a handful of states (Bihar, Madhya Pradesh,
  Odisha, Rajasthan for 2021/2026; an older 2006-2016 report also covered
  Maharashtra, UP, Chhattisgarh, Jharkhand) — never nationwide, and never
  Karnataka or Tamil Nadu. One genuinely national alternative exists:
  "Population Estimates for Districts and Parliamentary Constituencies in
  India, 2020" (Harvard Dataverse), built from WorldPop satellite-based
  gridded population summed over 2020 district boundaries, covering all
  736 districts. **Not yet adopted** — it's a modelled estimate rather
  than a measured census figure, and switching the population source
  would affect the D-HAI formula currently being built, so this is
  flagged for a team decision rather than changed unilaterally. Current
  default remains Census 2011, consistent with the proposal.

## 7. Reusable Pipeline

`merge_pipeline.py` generalizes the pilot's one-off script: takes any RHS
extract + any state list, applies the same crosswalk/fuzzy-match/exact-match
logic, and outputs both the merged file and a `.review.csv` listing every
non-exact match for manual review before trusting it. Verified to reproduce
the pilot's exact 629-row result before being adopted.

