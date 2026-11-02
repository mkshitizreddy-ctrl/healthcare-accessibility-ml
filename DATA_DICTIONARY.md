# Data Dictionary

Column reference for the data-pipeline outputs in `processed/`. For methods and how these files were built, see `DATA_SOURCES.md`: §9 covers the district merge, §11 the 2011 units, §12 the flags, §13 the 2020 population and §14 the audit.

**Conventions**

- **`year`:** an RHS reporting year (`2019-20`, `2020-21`, `2021-22`). Counts are as on 31 March of the later calendar year.
- **Facility counts:** the number of *functional* facilities reported in RHS Section II. RHS covers **rural** public health infrastructure only.
- **`*_per_100k`:** count ÷ Census-2011 population × 100,000.
- **Unit:** a Census-2011 boundary unit, either one 2011 district or a cluster of 2011 districts linked by a later split. A unit's ID is `U` + the lowest member Census-2011 district code, zero-padded to 3 digits.
- **Booleans:** `True` / `False`.

Downstream modelling files (`processed/national_dhai_results.csv`, `processed/national_temporal_ml_dataset.csv`, `results/`) are owned by the modelling stage. They are documented in `processed/national_dhai_metadata.json` and the README.

---

## 1. `processed/national_all_years_2011units.csv`: modelling panel

1,854 rows = 618 units × 3 years. One row per (`unit_id`, `year`); the panel is balanced.

| Column | Type | Description |
|---|---|---|
| `unit_id` | str | Stable unit identifier, e.g. `U538`. **Primary key with `year`.** |
| `state` | str | State/UT (LGD spelling). |
| `unit_name` | str | Census-2011 names of member districts, joined with ` + `. |
| `unit_codes` | str | Member Census-2011 district codes, `;`-separated. |
| `year` | str | RHS reporting year. |
| `n_census_districts` | int | Number of 2011 districts in the unit (>1 for 12 merged units). |
| `n_rhs_rows` | int | Number of RHS district rows summed into this unit-year. |
| `rhs_districts` | str | Original RHS district names summed, `; `-separated (audit trail). |
| `is_aggregated` | bool | `True` if the unit combines more than one 2011 district or RHS row. |
| `rows_below_max` | bool | `True` if this unit-year has fewer RHS rows than the unit's maximum across years. This happens when a child district is not yet reported separately; facility totals were checked to be continuous. |
| `population` | int | Census-2011 population, the sum over member districts. Constant across years. |
| `rural_hh_share_2011` | float | Rural ÷ total households in Census 2011, summed over member districts. Range 0–1. |
| `is_urban_unit` | bool | `rural_hh_share_2011 < 0.10` (10 units). RHS rural counts are about 0 by construction here, not because the unit is underserved. |
| `sub_centres` | int | Functional Sub Centres. |
| `phcs` | int | Functional Primary Health Centres. |
| `chcs` | int | Functional Community Health Centres. |
| `sub_divisional_hospital` | int | Functional Sub-Divisional Hospitals. |
| `district_hospital` | int | Functional District Hospitals. |
| `sub_centres_per_100k` | float | `sub_centres / population × 1e5`. |
| `phcs_per_100k` | float | `phcs / population × 1e5`. |
| `chcs_per_100k` | float | `chcs / population × 1e5`. |
| `sub_divisional_hospital_per_100k` | float | `sub_divisional_hospital / population × 1e5`. |
| `district_hospital_per_100k` | float | `district_hospital / population × 1e5`. |
| `anomaly_reason` | str | Reason text from `raw/known_anomalies.csv`; empty if none. |
| `known_anomaly` | bool | `True` for 8 unit-years with documented source anomalies: 7 Jharkhand units in 2020-21 and Tuensang in 2019-20. |

## 2. `processed/national_t_to_tplus1_2011units.csv`: temporal pairs

1,236 rows = 618 units × 2 transitions (2019-20 → 2020-21 and 2020-21 → 2021-22). Suffix `_t` means year *t*; suffix `_tp1` means year *t+1*.

| Column | Type | Description |
|---|---|---|
| `unit_id`, `state`, `unit_name` | str | As in §1. |
| `population` | int | Census-2011 population (same for *t* and *t+1*). |
| `is_urban_unit` | bool | As in §1. |
| `year_t`, `year_tp1` | str | Reporting years of the pair. |
| `n_rhs_rows_t`, `n_rhs_rows_tp1` | int | RHS rows summed in each year. |
| `known_anomaly_t`, `known_anomaly_tp1` | bool | Anomaly flag in each year. |
| `sub_centres_t` … `district_hospital_t` | int | The five facility counts in year *t*. |
| `sub_centres_tp1` … `district_hospital_tp1` | int | The five facility counts in year *t+1*. |

Per-100k rates are not stored here. Compute them as `count / population × 1e5`.

## 3. `processed/unit_population_2020.csv`: alternative denominator (sensitivity only)

618 rows, one per unit.

| Column | Type | Description |
|---|---|---|
| `unit_id`, `unit_name` | str | As in §1. |
| `population_2011` | int | Census-2011 population (same as §1 `population`). |
| `population_2020` | float | Harvard/WorldPop 2020 modelled population, summed over the 2020 districts mapped to the unit. |
| `n_harvard_districts` | int | Number of Harvard 2020 districts mapped to the unit. |
| `growth_2011_2020` | float | `population_2020 / population_2011`. The national median is about 1.14. |
| `pop2020_plausible` | bool | `True` if growth is in [0.90, 1.50]. 34 units are `False`, most likely because the source's boundary files assigned population to the wrong district. |

## 4. `processed/unit_membership.csv`: unit → 2011 districts

640 rows, one per Census-2011 district in the panel.

| Column | Type | Description |
|---|---|---|
| `unit_id` | str | Unit the district belongs to. |
| `code` | int | Census-2011 district code. |
| `census_name` | str | Census-2011 district name. |
| `pop2011` | int | Census-2011 district population. |

## 5. `processed/national_all_years_merged.csv`: district-level source table

2,178 rows, one per RHS district row per year. Districts are in **current (post-2011) boundaries**. This is the input to the unit re-aggregation; use §1 for modelling.

| Column | Type | Description |
|---|---|---|
| `state` | str | State/UT (LGD spelling). |
| `district` | str | District name **as printed in RHS**. |
| `sub_centres` … `district_hospital` | int | The five facility counts (as in §1). |
| `year` | str | RHS reporting year. |
| `lgd_matched_name` | str | Matched LGD district name; empty if unmatched. |
| `district_census2011_code` | float | Census-2011 code from LGD. Blank for 263 rows: 256 districts created after 2011 (LGD code `000`) and 7 unmatched rows (where `match_type = none`). Stored as float because of the blanks; cast to int to use it. |
| `match_type` | str | `exact` (1,965), `crosswalk` (206) or `none` (7). |
| `population` | float | Census-2011 population when a direct code match exists; blank for 263 rows. These rows are resolved in §1. |

## Supporting inputs

| File | Description |
|---|---|
| `raw/lineage/district_lineage.csv` | Post-2011 child district → Census-2011 parent code(s), with confidence and notes. |
| `raw/known_anomalies.csv` | `census2011_code, year, reason` for documented source anomalies. |
| `raw/population/harvard2020_name_crosswalk.csv` | Harvard 2020 district name → LGD name (spellings and renamings). |
| `raw/rhs/RHS_*.pdf` | Source reports. Not in git; see the README for source and MD5 checksums. |
