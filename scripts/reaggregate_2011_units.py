"""Re-aggregate district-year RHS rows to stable Census-2011 boundary units.

Why
---
Districts carved out after Census 2011 (LGD census code ``000``) have no 2011
population, and their *parents* are still joined to the undivided 2011
population while reporting post-split facility counts. Per-capita indicators
for parents are therefore biased downward by P_new / P_2011_undivided.

Fix: every post-2011 child is linked to its 2011 parent code(s)
(``raw/lineage/district_lineage.csv``). Census codes that share a child are
merged with union-find into one *unit*. Facility counts are summed per
(unit, year); population is the exact sum of member Census-2011 populations.

Outputs
-------
processed/national_all_years_2011units.csv   one row per (unit, year)
processed/national_t_to_tplus1_2011units.csv t -> t+1 pairs on units
processed/unit_membership.csv                unit -> member Census codes / names

Usage
-----
python scripts/reaggregate_2011_units.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MERGED = ROOT / "processed" / "national_all_years_merged.csv"
LINEAGE = ROOT / "raw" / "lineage" / "district_lineage.csv"
CENSUS = ROOT / "raw" / "population" / "census2011_districts.csv"
OUT_DIR = ROOT / "processed"

FACILITY_COLS = [
    "sub_centres", "phcs", "chcs", "sub_divisional_hospital", "district_hospital",
]
YEARS = ["2019-20", "2020-21", "2021-22"]


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[int, int] = {}

    def find(self, x: int) -> int:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]  # path halving
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(MERGED)
    lin = pd.read_csv(LINEAGE)
    lin["parents"] = lin["parent_census2011_codes"].astype(str).str.split(";").apply(
        lambda xs: [int(x) for x in xs]
    )
    census = pd.read_csv(CENSUS, usecols=["District code", "District name", "Population"])
    census = census.rename(columns={"District code": "code", "District name": "census_name",
                                    "Population": "pop2011"})
    return df, lin, census


def attach_parents(df: pd.DataFrame, lin: pd.DataFrame) -> pd.DataFrame:
    """Give every row a list of Census-2011 codes it belongs to."""
    df = df.copy()
    code = pd.to_numeric(df["district_census2011_code"], errors="coerce")
    has_code = code.notna() & (code != 0)

    # Child rows are keyed on LGD name (code 000) or raw RHS name (unmatched).
    key_name = df["lgd_matched_name"].where(df["lgd_matched_name"].notna(), df["district"])
    lin_map = {(r.state, r.child_name): r.parents for r in lin.itertuples()}
    df["members"] = [
        [int(c)] if ok else lin_map.get((s, n))
        for ok, c, s, n in zip(has_code, code, df["state"], key_name)
    ]

    missing = df[df["members"].isna()]
    if len(missing):
        raise ValueError(f"No lineage for {len(missing)} rows:\n"
                         f"{missing[['state', 'district', 'year']].to_string()}")
    unused = set(lin_map) - set(zip(df["state"], key_name))
    if unused:
        print(f"[warn] lineage entries never used: {sorted(unused)}")
    return df


def build_units(df: pd.DataFrame, census: pd.DataFrame) -> pd.DataFrame:
    uf = UnionFind()
    for members in df["members"]:
        for m in members:
            uf.union(members[0], m)
    df = df.copy()
    df["unit_root"] = df["members"].apply(lambda ms: uf.find(ms[0]))

    all_codes = sorted({m for ms in df["members"] for m in ms})
    mem = pd.DataFrame({"code": all_codes})
    mem["unit_root"] = mem["code"].map(uf.find)
    mem = mem.merge(census, on="code", how="left")
    if mem["pop2011"].isna().any():
        raise ValueError(f"Census codes without population: {mem[mem.pop2011.isna()].code.tolist()}")

    units = (mem.sort_values("code").groupby("unit_root")
             .agg(unit_codes=("code", lambda s: ";".join(map(str, s))),
                  unit_name=("census_name", lambda s: " + ".join(s)),
                  n_census_districts=("code", "size"),
                  population=("pop2011", "sum"))
             .reset_index())
    units["unit_id"] = "U" + units["unit_codes"].str.split(";").str[0].str.zfill(3)
    return df, units, mem


def aggregate(df: pd.DataFrame, units: pd.DataFrame) -> pd.DataFrame:
    g = (df.groupby(["unit_root", "year"])
           .agg(state=("state", "first"),
                n_rhs_rows=("district", "size"),
                rhs_districts=("district", lambda s: "; ".join(sorted(s))),
                **{c: (c, "sum") for c in FACILITY_COLS})
           .reset_index())
    out = g.merge(units, on="unit_root", how="left")

    # Coverage flag: a unit-year with fewer RHS rows than its max across years
    # may be missing a constituent district (or reflect a later split) -> inspect.
    out["max_rhs_rows"] = out.groupby("unit_root")["n_rhs_rows"].transform("max")
    out["rows_below_max"] = out["n_rhs_rows"] < out["max_rhs_rows"]
    out["is_aggregated"] = out["n_census_districts"].gt(1) | out["n_rhs_rows"].gt(1)

    for c in FACILITY_COLS:
        out[f"{c}_per_100k"] = out[c] / out["population"] * 1e5  # Shape: [N_unit_years]

    cols = (["unit_id", "state", "unit_name", "unit_codes", "year", "n_census_districts",
             "n_rhs_rows", "rhs_districts", "is_aggregated", "rows_below_max", "population"]
            + FACILITY_COLS + [f"{c}_per_100k" for c in FACILITY_COLS])
    return out[cols].sort_values(["state", "unit_id", "year"]).reset_index(drop=True)


def make_pairs(panel: pd.DataFrame) -> pd.DataFrame:
    keep = ["unit_id", "state", "unit_name", "population", "n_rhs_rows"] + FACILITY_COLS
    pairs = []
    for y0, y1 in zip(YEARS[:-1], YEARS[1:]):
        a = panel.loc[panel.year == y0, keep + ["year"]]
        b = panel.loc[panel.year == y1, ["unit_id", "year", "n_rhs_rows"] + FACILITY_COLS]
        p = a.merge(b, on="unit_id", suffixes=("_t", "_tp1"))
        pairs.append(p)
    return pd.concat(pairs, ignore_index=True)


def validate(raw: pd.DataFrame, panel: pd.DataFrame) -> None:
    # 1. Facility totals conserved per year (no row dropped or double counted).
    for c in FACILITY_COLS:
        a = raw.groupby("year")[c].sum()
        b = panel.groupby("year")[c].sum()
        assert (a == b).all(), f"facility totals not conserved for {c}:\n{a - b}"
    # 2. Every unit has a population.
    assert panel["population"].notna().all()
    # 3. Each unit appears at most once per year.
    assert not panel.duplicated(["unit_id", "year"]).any()


def main() -> None:
    raw, lin, census = load_inputs()
    df = attach_parents(raw, lin)
    df, units, mem = build_units(df, census)
    panel = aggregate(df, units)
    validate(raw, panel)
    pairs = make_pairs(panel)

    panel.to_csv(OUT_DIR / "national_all_years_2011units.csv", index=False)
    pairs.to_csv(OUT_DIR / "national_t_to_tplus1_2011units.csv", index=False)
    mem.merge(units[["unit_root", "unit_id"]], on="unit_root")[
        ["unit_id", "code", "census_name", "pop2011"]
    ].sort_values(["unit_id", "code"]).to_csv(OUT_DIR / "unit_membership.csv", index=False)

    print(f"rows in : {len(raw)} district-years")
    print(f"rows out: {len(panel)} unit-years | {panel.unit_id.nunique()} units | "
          f"population coverage {panel.population.notna().mean():.1%}")
    print(f"pairs   : {len(pairs)}")
    print(f"aggregated units: {units.query('n_census_districts > 1').shape[0]} multi-parent clusters")


if __name__ == "__main__":
    main()
