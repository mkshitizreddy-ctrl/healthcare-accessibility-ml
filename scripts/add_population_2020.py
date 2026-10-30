"""Map Harvard 2020 modelled district populations onto Census-2011 boundary units.

Source: Wang, Kim & Subramanian (2021), "Population Estimates for Districts and
Parliamentary Constituencies in India, 2020", Harvard Dataverse,
https://doi.org/10.7910/DVN/RXYJR6 (CC0). WorldPop 100 m raster summed over 2020
district boundaries (736 districts; Mumbai + Mumbai Suburban reported together).

Chain: Harvard name -> LGD district (exact normalised name, else
raw/population/harvard2020_name_crosswalk.csv) -> Census-2011 code (LGD, or
raw/lineage/district_lineage.csv for post-2011 districts) -> unit_id
(processed/unit_membership.csv). Populations are summed per unit.

Output: processed/unit_population_2020.csv
    unit_id, unit_name, population_2011, population_2020, n_harvard_districts,
    growth_2011_2020, pop2020_plausible

For sensitivity analysis only; the primary denominator stays Census 2011.

Usage: python scripts/add_population_2020.py
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HARVARD = ROOT / "raw" / "population" / "harvard_2020_district_population.xlsx"
NAME_XWALK = ROOT / "raw" / "population" / "harvard2020_name_crosswalk.csv"
LGD = ROOT / "raw" / "lgd" / "lgd_districts.csv"
LINEAGE = ROOT / "raw" / "lineage" / "district_lineage.csv"
MEMBERSHIP = ROOT / "processed" / "unit_membership.csv"
PANEL = ROOT / "processed" / "national_all_years_2011units.csv"
OUT = ROOT / "processed" / "unit_population_2020.csv"
PLAUSIBLE_GROWTH = (0.90, 1.50)  # national 2011->2020 growth is ~1.14


def norm(s: str) -> str:
    s = str(s).lower().replace("&", "and")
    s = re.sub(r"^the\s+", "", s)
    return re.sub(r"[^a-z]", "", s)


def norm_state(s: str) -> str:
    return norm(s).replace("nctof", "")


def main() -> None:
    h = pd.read_excel(HARVARD, sheet_name="Districts")
    h.columns = ["harvard_state", "harvard_label", "population_2020"]
    h["harvard_district"] = h["harvard_label"].str.rsplit(",", n=1).str[0].str.strip()

    # 1. Harvard name -> LGD name (manual crosswalk overrides, else identity).
    xw = pd.read_csv(NAME_XWALK, keep_default_na=False)
    override = dict(zip(zip(xw.harvard_state, xw.harvard_district), xw.lgd_district))
    h["lgd_district"] = [override.get((s, d), d)
                         for s, d in zip(h.harvard_state, h.harvard_district)]
    excluded = h[h["lgd_district"].eq("")]
    h = h[h["lgd_district"].ne("")].copy()

    # 2. LGD name -> Census-2011 code(s).
    lgd = pd.read_csv(LGD, dtype=str)
    lgd["key"] = lgd.state_name_english.map(norm_state) + "|" + lgd.district_name_english.map(norm)
    lgd["code"] = pd.to_numeric(lgd.district_census2011_code, errors="coerce")
    code_by_key = dict(zip(lgd.key, lgd.code))

    lin = pd.read_csv(LINEAGE)
    lin_by_key = {norm_state(s) + "|" + norm(c): [int(x) for x in str(p).split(";")]
                  for s, c, p in zip(lin.state, lin.child_name, lin.parent_census2011_codes)}

    def to_codes(state: str, district: str) -> list[int] | None:
        st = norm_state(state)
        # Harvard uses the merged UT name; LGD prefixes "The".
        st = {"dadraandnagarhavelianddamananddiu": "dadraandnagarhavelianddamananddiu"}.get(st, st)
        key = st + "|" + norm(district)
        code = code_by_key.get(key)
        if code is None:  # LGD state spelling differs (e.g. leading "The")
            cands = [k for k in code_by_key if k.endswith("|" + norm(district)) and st in k]
            code = code_by_key[cands[0]] if len(cands) == 1 else None
        if code is not None and code > 0:
            return [int(code)]
        return lin_by_key.get(key)

    h["codes"] = [to_codes(s, d) for s, d in zip(h.harvard_state, h.lgd_district)]
    unmatched = h[h["codes"].isna()]
    if len(unmatched):
        raise ValueError("Harvard districts without a Census-2011 code:\n"
                         + unmatched[["harvard_state", "harvard_district", "lgd_district"]].to_string())

    # 3. Census code -> unit. All parents of one child sit in the same unit by construction.
    mem = pd.read_csv(MEMBERSHIP)
    unit_by_code = dict(zip(mem.code, mem.unit_id))
    h["unit_ids"] = h["codes"].apply(lambda cs: sorted({unit_by_code.get(c) for c in cs}, key=str))
    # Districts of states absent from the RHS panel have no unit -> reported, not an error.
    not_in_panel = h[h["unit_ids"].apply(lambda u: u == [None])]
    h = h.drop(not_in_panel.index)
    bad = h[h["unit_ids"].apply(lambda u: len(u) != 1 or u[0] is None)]
    if len(bad):
        raise ValueError(f"Districts mapping to 0 or >1 units:\n{bad[['harvard_district', 'codes', 'unit_ids']]}")
    h["unit_id"] = h["unit_ids"].str[0]

    out = (h.groupby("unit_id")
             .agg(population_2020=("population_2020", "sum"),
                  n_harvard_districts=("harvard_district", "size"))
             .reset_index())
    pop11 = pd.read_csv(PANEL).drop_duplicates("unit_id")[["unit_id", "unit_name", "population"]]
    out = pop11.merge(out, on="unit_id", how="left").rename(columns={"population": "population_2011"})
    out["growth_2011_2020"] = out["population_2020"] / out["population_2011"]  # Shape: [N_units]
    # WorldPop totals over community shapefiles can misplace population across neighbouring
    # districts (source README warns of this). Flag growth outside a plausible 2011->2020 band.
    out["pop2020_plausible"] = out["growth_2011_2020"].between(PLAUSIBLE_GROWTH[0], PLAUSIBLE_GROWTH[1])

    missing = out[out.population_2020.isna()]
    out.to_csv(OUT, index=False)

    print(f"Harvard districts: {len(h) + len(excluded) + len(not_in_panel)} | mapped {len(h)} | "
          f"excluded {len(excluded)} ({', '.join(excluded.harvard_district)}) | "
          f"not in RHS panel {len(not_in_panel)} ({', '.join(not_in_panel.harvard_district)})")
    print(f"units with 2020 population: {out.population_2020.notna().sum()} / {len(out)}")
    if len(missing):
        print(f"[warn] units without 2020 population: {missing.unit_name.tolist()}")
    print(f"implausible 2011->2020 growth (outside {PLAUSIBLE_GROWTH}): "
          f"{(~out.pop2020_plausible).sum()} units")
    print(out["growth_2011_2020"].describe().round(3).to_string())


if __name__ == "__main__":
    main()
