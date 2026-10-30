# Data Sources & Methodology Notes

This document records the sources used to build the healthcare accessibility dataset, the decisions made while joining the data, the validation checks performed, and the limitations that need to be considered when using the dataset for analysis and modelling.

## 1. Source Catalog

| File | Source | Retrieved via | Notes |
|---|---|---|---|
| `raw/rhs/RHS_2019-20.pdf` | Ministry of Health & Family Welfare, Rural Health Statistics 2019-20 | ruralindiaonline.org (PARI library mirror) | Scanned PDF, no text layer on the direct print-to-PDF copy |
| `raw/rhs/RHS_2020-21.pdf` | Ministry of Health & Family Welfare, Rural Health Statistics 2020-21 | archive.org (PARI.rural-health-statistics-2020-21), "PDF" download option | Has OCR text layer — Ctrl+F works |
| `raw/rhs/RHS_2021-22.pdf` | Ministry of Health & Family Welfare, Rural Health Statistics 2021-22 | archive.org (PARI.rural-health-statistics-2021-22), "PDF" download option | Has OCR text layer — Ctrl+F works |
| `raw/population/census2011_districts.csv` | Census of India 2011, district-level population | GitHub mirror (nishusharma1608/India-Census-2011-Analysis) | Community-compiled CSV of official Census 2011 figures |
| `raw/lgd/lgd_districts.csv` | Local Government Directory (LGD), Ministry of Panchayati Raj | data.gov.in — official LGD districts resource | Provides the `district_census2011_code` used as the join key |

**Table used from each RHS report:** Section II, "District-wise Health Care Infrastructure in India" — the district-level table containing Sub Centres, PHCs, CHCs, Sub Divisional Hospital, and District Hospital counts. RHS manpower data (doctors, nurses, health workers) is reported only at state/UT level through separate "Comparative Statement" tables. It cannot be treated as a genuinely district-level measurement.

## 2. Extraction & Verification

RHS district tables were extracted for the five pilot states (Karnataka, Maharashtra, Rajasthan, Tamil Nadu, and Uttar Pradesh) across all three years. Every state's extracted row sums were checked against the report's own "Total Districts = ..." summary line and matched exactly in all 15 state-year combinations (5 states × 3 years).

The national dataset was subsequently assembled for the three RHS reporting years, 2019-20, 2020-21, and 2021-22. The extracted facility counts were checked against the RHS report's district-total lines wherever such a total was available. These checks help detect extraction errors, but do not independently establish that every individual district value in the source report is correct.

## 3. District Join: RHS → LGD → Population

Districts are linked across sources using the Local Government Directory (LGD) and the Census 2011 district codes, rather than relying on district names alone. RHS district names can differ from LGD names because of spelling variations, historical renaming, administrative changes, and differences in how districts are reported.

### Join process

The pipeline follows this process:

1. Normalize district-name text, including case and punctuation.
2. Attempt an exact district-name match within the same state.
3. Apply explicit crosswalk entries for known name variations and reviewed historical mappings.
4. Record fuzzy string-matching candidates for manual review. A fuzzy candidate is not automatically accepted as a valid district match and does not supply an LGD or Census code.
5. Use the accepted LGD `district_census2011_code` to join the district to the Census 2011 population data.
6. Write non-exact and unresolved records to a `.review.csv` file for inspection.

The crosswalk is maintained in `scripts/merge_pipeline.py`. It has been expanded as additional RHS district names have been examined against the available LGD records. The crosswalk remains an evolving record of name mappings, not a substitute for checking the historical and administrative relationship between districts.

### Why automatic fuzzy matching is disabled

Naive fuzzy matching without manual review produced two silent wrong matches:

- "Faizabad" (the former name associated with Ayodhya, Uttar Pradesh) was incorrectly matched to "Firozabad", a different Uttar Pradesh district.
- "Sant Ravidas Nagar" (the former name associated with Bhadohi, Uttar Pradesh) was incorrectly matched to "Sant Kabir Nagar", a different Uttar Pradesh district.

These errors demonstrate that a high string-similarity score does not establish that two names refer to the same district.

The pipeline therefore records fuzzy candidates for review but does not automatically accept their codes. Every non-exact match must be reviewed before it is trusted. Explicit crosswalk entries also require appropriate scrutiny: the existence of a target name in the LGD file confirms that the target is present in that directory, but does not alone prove the historical correspondence.

### Examples of crosswalk entries

The following entries were documented during the pilot. The operational crosswalk in `scripts/merge_pipeline.py` may contain additional entries added during the national build.

| RHS name (old or alternate) | LGD target name | State | Mapping context |
|---|---|---|---|
| Belgaum | Belagavi | Karnataka | Official renaming |
| Bellary | Ballari | Karnataka | Official renaming |
| Bijapur | Vijayapura | Karnataka | Official renaming |
| Gulbarga | Kalaburagi | Karnataka | Official renaming |
| Mysore | Mysuru | Karnataka | Official renaming |
| Aurangabad | Chhatrapati Sambhajinagar | Maharashtra | Official renaming (2023) |
| Osmanabad | Dharashiv | Maharashtra | Official renaming (2023) |
| Bid | Beed | Maharashtra | Alternate spelling |
| Faizabad | Ayodhya | Uttar Pradesh | Historical name and renaming |
| Allahabad | Prayagraj | Uttar Pradesh | Official renaming |
| C S M Nagar | Amethi | Uttar Pradesh | Historical name and renaming |
| Jyotiba Phule Nagar | Amroha | Uttar Pradesh | Historical name and renaming |
| Kashi Ram Nagar | Kasganj | Uttar Pradesh | Historical name and renaming |
| Lakhimpur Kheri | Kheri | Uttar Pradesh | Alternate or shortened name |
| Maunathbhanjan | Mau | Uttar Pradesh | Alternate or shortened name |
| Sant Ravidas Nagar | Bhadohi | Uttar Pradesh | Historical name and renaming |
| Tuticorin | Thoothukkudi | Tamil Nadu | Official renaming |

These are examples, not an exhaustive list of all mappings used by the nationwide pipeline. The actual script is the operational reference for the mappings applied during a run.

## 4. Known Limitations

- **Districts without a Census 2011 population match**

  Some current LGD districts do not have a direct Census 2011 population match. The LGD code `000` is used in the current dataset for records that cannot be linked through a valid Census 2011 district code.

  A code of `000` does not, by itself, establish why a district lacks a population match or confirm that it was created after 2011. Administrative reorganizations, boundary changes, differences in district definitions, and source limitations need to be considered before deciding how to handle each case.

  These records need a separate population-data decision: use an appropriate alternative source, develop a defensible method for estimating population, or exclude the affected observations from analyses that require population. Missing population must not be silently interpreted as zero.

- **Mumbai / Mumbai Suburban combined-entry mismatch**

  In RHS 2019-20, Mumbai and Mumbai Suburban are reported together as "Brihan Mumbai", while LGD and Census records treat them as separate districts. The combined RHS row cannot be assigned cleanly to either individual district without additional information or a defensible allocation method. It is therefore left unmatched.

- **Split districts and administrative changes**

  District names and boundaries can change over time. Some RHS records, including Warangal Rural/Urban and Aizawl East/West, cannot be mapped cleanly to a single LGD district using a one-to-one name crosswalk. These records remain unmatched rather than being assigned an arbitrary district code.

- **Manpower data is state-level, not district-level**

  RHS reports doctors, nurses, and health worker counts only at state/UT level in the relevant comparative tables. Any manpower-based feature derived from those tables would be a state-level value applied uniformly to districts in that state, not a genuine district-level measurement. This limitation must be stated explicitly in any final report or model interpretation.

- **LGD and Census code formatting**

  LGD and Census files use different formats for some district codes. For example, LGD may store a code with leading zeros such as `099`, while the Census file stores the corresponding code as `99`. Codes must be normalized consistently before joining; otherwise, valid matches can be missed. The pipeline has been updated to normalize codes before the population join.

## 5. Pilot Test Result

The pilot dataset contained 629 district-year rows across five states and three years, with 95.5% population coverage. Extracted state-year totals were checked against the RHS report's district-total lines, and the pilot's known join limitations were documented.

The pilot results established a working extraction and merging process. They did not eliminate the need for additional crosswalk review, population-source decisions, or validation when extending the pipeline nationwide.

## 6. National-Scale Audit

Before scaling beyond the five pilot states, the LGD and Census files were audited for code-formatting issues and missing Census 2011 population links.

- **Leading-zero code issue:** A national audit identified 99 district codes affected by inconsistent leading-zero formatting. Normalizing codes before joining resolved the identified formatting problem.

- **Districts without a Census 2011 population match:** The earlier national audit identified 125 of 785 LGD districts without a Census 2011 population match (15.9%). The national merged dataset subsequently showed 256 district-year rows with LGD Census code `000`. These are different measures: the first counts LGD districts in the audit, while the second counts rows across the three RHS reporting years. They should not be treated as interchangeable.

- **Incremental crosswalk development:** The crosswalk has been expanded as additional RHS district names have been examined and compared against LGD records. One previously documented example is Madhya Pradesh's Hoshangabad → Narmadapuram renaming. Newly added mappings should be reviewed and maintained in the pipeline as further district names and administrative changes are encountered.

- **Age of Census 2011 population data:** Census 2011 population figures are old relative to the RHS reporting years. A nationwide alternative population source has not been adopted in this pipeline. A possible alternative is the study "Population Estimates for Districts and Parliamentary Constituencies in India, 2020" available through Harvard Dataverse, which uses modelled population estimates. Because modelled estimates are not identical to measured Census figures and may affect the D-HAI formula, the choice of population source requires a documented project decision. The current dataset continues to use Census 2011 population where a direct link is available.

## 7. Reusable Pipeline

`scripts/merge_pipeline.py` generalizes the pilot's merging process. It accepts an RHS extract, LGD district records, and Census population data, then produces a merged dataset and a `.review.csv` file containing non-exact and unresolved matches.

The pipeline supports exact matching and explicit crosswalk entries. Fuzzy candidates may be recorded for manual inspection, but their codes are not automatically accepted. The review file should be examined before relying on non-exact matches in downstream analysis.

The nationwide pipeline output is stored at:

`processed/national_all_years_merged.csv`

The pipeline has been used to reproduce the 629-row pilot result and to build the national dataset. Future changes to crosswalk entries or matching logic should be tested against a saved baseline, with row counts, keys, match classifications, and population values compared before promotion.

## 8. National Health Profile (NHP) — Resolved: Not Adopted

NHP was flagged in the feasibility note as "use if compatible." The reviewed NHP material is structured around six chapters: Demographic, Socio-Economic, Health Status, Health Finance, Human Resources, and Health Infrastructure. The indicators relevant to this project are reported at state/UT or national level rather than as consistent district-level tables.

The district-level mentions found in NHP material were incidental counts, rather than structured district-level indicators suitable for use as model features.

**Decision: NHP was not adopted as a district-level feature source.** RHS, LGD, and Census data remain the principal sources for the current dataset, subject to the limitations documented here.

## 9. National Dataset Build — All States/UTs Across Three Years

### Final dataset

**Output:** `processed/national_all_years_merged.csv`

The promoted dataset contains 2,178 district-year rows (2,166 before Sikkim was added on 2026-10-30; see §14):

| RHS reporting year | District-year rows |
|---|---:|
| 2019-20 | 706 |
| 2020-21 | 735 |
| 2021-22 | 737 |
| **Total** | **2,178** |

Extracted facility counts were checked against the RHS report's own "Total Districts" line wherever such a total was available.

### Final matching results

The final promoted dataset has the following match classifications:

| Match type | Rows | Meaning |
|---|---:|---|
| Exact | 1,965 | Matched through the exact-name process |
| Crosswalk | 206 | Matched through explicit crosswalk entries |
| Fuzzy | 0 | No fuzzy candidate was automatically accepted as a match |
| None | 7 | No valid one-to-one LGD match was assigned |
| **Total** | **2,178** | |

The crosswalk category includes mappings previously classified as fuzzy and subsequently represented through explicit crosswalk entries. This change in classification does not, by itself, change the population values associated with those rows.

### Population coverage

Population is available for 1,915 of the 2,178 rows, giving coverage of **87.9%**. (At district level; the Census-2011 unit dataset in §11 has 100% coverage.)

The remaining 263 rows have no population value:

- **256 rows** have LGD Census 2011 district code `000` and therefore lack a direct Census 2011 population join through that code.
- **7 rows** remain unmatched to an LGD district.

The `000` code does not by itself prove that every affected district was created after the 2011 Census. These rows require a separate population-source decision before analyses that depend on complete population coverage.

### Unmatched district-year rows

The following seven rows remain unmatched:

| State | Year | RHS district |
|---|---|---|
| Telangana | 2019-20 | Warangal Rural |
| Telangana | 2019-20 | Warangal Urban |
| Mizoram | 2019-20 | Aizawl East |
| Mizoram | 2019-20 | Aizawl West |
| Telangana | 2020-21 | Warangal Rural |
| Telangana | 2020-21 | Warangal Urban |
| Maharashtra | 2019-20 | Brihan Mumbai |

These records involve split or combined district reporting that cannot be represented safely by a simple one-to-one name crosswalk. They have been left unmatched rather than assigned a potentially incorrect code.

### Structural validation

The promoted dataset was checked against the pre-promotion baseline and the tested candidate output.

The checks found:

- 2,166 rows retained.
- No duplicate `state + district + year` keys.
- No rows added or dropped during crosswalk promotion.
- No duplicate LGD district-year targets introduced by the reviewed mappings.
- No changes to population values or Census codes in the structural comparison between the baseline and promoted candidate.
- 122 rows previously labelled as fuzzy were reclassified as explicit crosswalk matches; population values remained unchanged.
- Final matching classifications are 1,965 exact, 194 crosswalk, and 7 unmatched, with zero automatically accepted fuzzy matches.

These checks establish structural consistency and preservation of the existing population joins. They do not independently prove the historical correctness of every crosswalk entry. Mapping accuracy still depends on the quality of the source evidence and review of individual mappings.

### Transcription issues found and handled

- Text fused across rows or state boundaries in scanned PDFs was separated and rechecked against totals.
- District and state names wrapped across lines were rejoined.
- Duplicated or corrupted pasted blocks caused by page overlap were checked, and only the complete block was retained.
- Two Telangana rows in 2020-21 had a missing value; the missing column was identified by checking against the state total rather than guessing.
- One typo in Dadra & Nagar Haveli for 2020-21 was corrected through the same sum-check process.

### Join and parser issues found

- State names must match LGD spelling, including names such as "Jammu And Kashmir", "Andaman And Nicobar Islands", and "The Dadra And Nagar Haveli And Daman And Diu". A state-name mismatch can cause records to be missed.
- "Kamrup M" and "Kamrup R" previously fuzzy-matched to the same LGD district. Explicit crosswalk entries were added to prevent that collision.
- The name-normalization function strips digits. District names beginning with a number, such as "24 Parganas", therefore require careful handling in crosswalk keys and during extraction.
- A district named the same as its state, such as Puducherry, requires care when removing state prefixes from district names.
- Fuzzy string similarity must not be used as sufficient evidence for a district match. Fuzzy candidates are recorded for review but are not automatically assigned codes.

### Open items

- Decide how to obtain or estimate population for the 256 rows with LGD Census 2011 code `000`.
- Decide whether Census 2011 remains an appropriate population source for the final modelling period.
- Review and maintain the national crosswalk as additional historical names and administrative changes are encountered.
- Check cross-year consistency of facility counts, particularly where the source reports show unusual district-level changes.
- Ensure that downstream analysis accounts for missing population values and the seven unresolved district-year rows.

## 10. Known Anomaly: Jharkhand 2020-21 District Values

Cross-year comparison flagged that several Jharkhand districts' 2020-21 facility counts exactly match a different district's 2019-20 or 2021-22 values. Examples include Palamu's 2020-21 row matching Pashchimi Singhbhum's values in other years, and Ramgarh's 2020-21 row matching Purbi Singhbhum's values. Similar patterns were observed for Pakur, Ranchi, Sahebganj, and East/West Singhbhum.

The values were rechecked against a fresh copy of the RHS 2020-21 source table. The anomaly was confirmed to be present in the official RHS report itself rather than being introduced by the extraction process. The state total (3848, 350, 176, 13, 22) matched in the original extraction and the recheck.

The values have been left unchanged because the correct district-level figures could not be established from the available evidence. Altering the published government figures without verification would risk introducing additional errors.

Affected districts are Pakur, Palamu, Ramgarh, Ranchi, Sahebganj, Pashchimi Singhbhum, and Purbi Singhbhum for 2020-21. Any district-level model output for these seven districts in that year should be treated with caution.

## 11. Population Decision — Re-aggregation to Census-2011 Boundary Units

**Decision (adopted):** the primary modelling dataset uses stable Census-2011 boundary units instead of current LGD districts. Modelled current-boundary population estimates (Harvard Dataverse, 2020) are kept only as a possible sensitivity analysis.

**Why.** The 263 rows without population were not missing at random. 256 were districts carved out after 2011, concentrated in the Northeast, Telangana and Chhattisgarh. The other 7 were unmatched split or combined RHS entries. A second, less visible problem: the parent district of each split was still joined to its *undivided* 2011 population while reporting post-split facility counts. Its per-capita density was therefore biased downward by the factor $P_{\text{new}}/P_{2011}$. Example: Adilabad 2021-22 showed 126 sub-centres for 2.74M people (4.6 per 100k). The re-aggregated Adilabad unit has 455 sub-centres for the same 2.74M (16.6 per 100k). Dropping the code-`000` rows would not have fixed this parent bias.

**Method** (`scripts/reaggregate_2011_units.py`):

1. `raw/lineage/district_lineage.csv` links each post-2011 child (and the unmatched Warangal Rural/Urban, Aizawl East/West and Brihan Mumbai rows) to its Census-2011 parent code(s), with a `confidence` column.
2. Census codes that share a child are merged into one unit (union-find). Facility counts are summed per (unit, year), and population is the exact sum of member Census-2011 populations.
3. Validation asserts that national facility totals are conserved per year, that every unit has a population, and that each unit appears once per year.

**Result:** 2,178 district-year rows become 1,854 unit-year rows (618 units × 3 years), with a balanced panel and 100% population coverage. The temporal table has 1,236 pairs. 12 units merge several 2011 districts. The largest are NCT Delhi (all 9 districts, because the 2012 reorganisation redrew every boundary) and a Telangana cluster of Karimnagar, Medak, Warangal and Khammam (caused by the 2016 multi-parent reorganisation).

**Known costs and caveats**

- Spatial resolution is lower in Telangana, Delhi and Gujarat (Saurashtra). Results there describe larger areas.
- Lineage verification (2026-10-30): the six `medium` rows were checked against Wikipedia and the LGD village directory (2022 snapshot, [planemad/india-local-government-directory](https://github.com/planemad/india-local-government-directory)). Census 2011 village codes are contiguous within each 2011 district, so each new district's villages show which 2011 district block they fall in. Jangoan's parent was corrected to Warangal only: Gundala, the only mandal from Nalgonda, now sits in Yadadri Bhuvanagiri, so Nalgonda (with Suryapet and Yadadri) is a separate unit. The other five rows were confirmed. One caveat remains: the date of Gundala's transfer is unverified, and if it happened after the RHS reference dates, roughly 20 villages are assigned to the wrong unit. Warangal Rural is still `medium`. It has no effect on units, because Warangal is already merged with Karimnagar.
- `rows_below_max` flags unit-years with fewer RHS rows than in other years (children not yet reported separately). Facility totals for these units were continuous across years, with one exception: Tuensang 2019-20 (38 sub-centres vs 55–56 later), which reflects the RHS figures rather than the split.
- Census 2011 population is still stale relative to 2019–22.
- RHS covers rural infrastructure, so metro units (Mumbai, Chennai, Kolkata, Chandigarh) show zero or near-zero sub-centres. These should be excluded or flagged before D-HAI thresholds are calibrated.

## 12. Data-Quality Flags in the Unit Dataset

`scripts/reaggregate_2011_units.py` writes these columns to `processed/national_all_years_2011units.csv` (and their `_t` / `_tp1` versions to the pairs table):

| Column | Definition | Why |
|---|---|---|
| `rural_hh_share_2011` | Rural households ÷ all households, summed over the unit's Census-2011 districts | RHS measures *rural* infrastructure, so how meaningful its counts are depends on how rural the unit is. |
| `is_urban_unit` | `rural_hh_share_2011 < 0.10` (constant `URBAN_UNIT_MAX_RURAL_SHARE`) | Metro cores report about 0 sub-centres or PHCs because of how RHS is defined, not because they are underserved. Flagged: Mumbai, Kolkata, Chennai, Hyderabad, Bangalore, Srinagar, Chandigarh, NCT Delhi, Yanam, Mahe. |
| `known_anomaly`, `anomaly_reason` | Unit-year contains a documented source anomaly listed in `raw/known_anomalies.csv` | 8 unit-years: the seven Jharkhand districts in 2020-21 (§10) and Tuensang in 2019-20 (§11). |

The flags only mark rows; no rows are dropped. Whether to exclude or down-weight flagged rows is a modelling decision. To add a new anomaly, append a row (`census2011_code, year, reason`) to `raw/known_anomalies.csv` and re-run the script. The script stops with an error if a code doesn't belong to any unit.

## 13. Alternative Denominator: Harvard 2020 Modelled Population (Sensitivity Only)

**Source:** Wang W., Kim R., Subramanian S.V. (2021). *Population Estimates for Districts and Parliamentary Constituencies in India, 2020.* Harvard Dataverse, [doi:10.7910/DVN/RXYJR6](https://doi.org/10.7910/DVN/RXYJR6), CC0. The figures are WorldPop 2020 100 m raster counts summed over community-made (DataMeet) district shapefiles that follow 2020 boundaries. There are 736 districts, and Mumbai and Mumbai Suburban are reported together. Stored as `raw/population/harvard_2020_district_population.xlsx` (MD5 `9267ffaf1e493fc0b1bdfdd45d1d4010`, which matches the Dataverse record).

**Mapping** (`scripts/add_population_2020.py`): each Harvard district name is matched to its LGD district (normalised exact match, or the 100-row `raw/population/harvard2020_name_crosswalk.csv` for spelling variants and renamings). That gives its Census-2011 code, either directly from LGD or through `raw/lineage/district_lineage.csv` for post-2011 districts. The code gives the `unit_id`, and populations are summed per unit. Output: `processed/unit_population_2020.csv`.

**Result:** 734 of 736 districts are mapped, and all 618 units receive a 2020 population. Not mapped: Mirpur and Muzaffarabad (PoK, which has no RHS or LGD counterpart).

**Caveats**

- These are modelled estimates, not a census count. The source itself warns that the totals depend on how accurate the shapefiles are.
- 34 units have implausible 2011→2020 growth (outside 0.90–1.50, against a national median of about 1.14). Examples are Srinagar at 0.58 alongside Ganderbal at 4.90, and Hazaribagh at 0.69 alongside Jamtara at 1.88. These look like population assigned to the neighbouring district by the shapefiles, not real change. They are flagged as `pop2020_plausible = False`.
- Use this file only to check whether D-HAI rankings and labels hold up when the denominator changes. The primary denominator stays Census 2011.

**Gap found and resolved:** Sikkim was missing from every RHS extract. It has now been added; see §14.

## 14. Completeness Audit and Sikkim Addition (2026-10-30)

**Audit.** `scripts/audit_rhs_totals.py` reads every "Total Districts = N" line in RHS Section II of all three reports (with `pdftotext`). It checks that some state-year in `processed/national_all_years_merged.csv` has exactly the same district count and five facility totals. The match is made on the numbers rather than state names, because the PDF splits state cells across lines.

Before this fix, every multi-district state-year reconciled exactly except **Sikkim, which was missing in all three years** (in 2019-20 its table rows break across pages 117–118). Single-district UTs (Chandigarh, Lakshadweep) have no total line and cannot be checked this way.

**Sikkim addition.** The 12 rows (4 districts × 3 years) were transcribed into `processed/rhs_sikkim_all_years.csv`. RHS uses the pre-2021 names East, North, South and West (with "District" added from 2020-21). Crosswalk entries in `scripts/merge_pipeline.py` map them to the LGD names Gangtok (244), Mangan (241), Namchi (243) and Gyalshing (242). Every year matches the report's Sikkim total line:

| Year | Sub Centres | PHCs | CHCs | SDH | DH |
|---|---:|---:|---:|---:|---:|
| 2019-20 | 153 | 25 | 2 | 1 | 4 |
| 2020-21 | 153 | 26 | 2 | 1 | 4 |
| 2021-22 | 153 | 26 | 2 | 1 | 4 |

The merge output (`processed/rhs_sikkim_all_years_merged.csv`, 12/12 matched by crosswalk, 100% population) was appended to `processed/national_all_years_merged.csv`. All downstream outputs were then rebuilt: 618 units, 1,854 unit-years, 1,236 pairs, and Harvard 2020 population for all 618 units. RHS still reports 4 Sikkim districts in 2021-22, so Pakyong and Soreng (created in 2021) don't need lineage rows yet.

**Note:** the copies of `national_all_years_merged.csv` at the repo root and in `clean_dataset/` are not updated by the pipeline. They now lack the Sikkim rows.
