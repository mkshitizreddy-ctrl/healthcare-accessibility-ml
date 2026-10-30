"""Reconcile the merged dataset against each RHS report's own state totals.

Every multi-district state block in RHS Section II ("District-wise Health Care
Infrastructure") ends with a line such as

    Total Districts = 33       13589       2409    685     22     30

This script extracts those lines from the PDFs and checks that some state-year in
the merged data has exactly the same district count and five facility totals, and
vice versa. Matching is on the numbers, not on state names, because pdftotext
splits multi-line state cells unpredictably.

A missing state (as Sikkim was before 2026-10-30) or a dropped or mistyped district
shows up as an unmatched total. Single-district UTs have no total line and are
reported as "not checkable".

Requires: pdftotext (poppler-utils).

Usage:
    python scripts/audit_rhs_totals.py \
        --pdf 2019-20=raw/rhs/RHS_2019-20.pdf \
        --pdf 2020-21=raw/rhs/RHS_2020-21.pdf \
        --pdf 2021-22=raw/rhs/RHS_2021-22.pdf
Exit code 1 if anything fails to reconcile.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MERGED = ROOT / "processed" / "national_all_years_merged.csv"
COLS = ["sub_centres", "phcs", "chcs", "sub_divisional_hospital", "district_hospital"]
TOTAL_RE = re.compile(r"Total Districts\s*=\s*(\d+)" + r"\s+(\d+)" * 5)


def pdf_totals(year: str, pdf: Path) -> pd.DataFrame:
    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                          capture_output=True, text=True, check=True).stdout
    rows = [(year, *map(int, m.groups())) for m in TOTAL_RE.finditer(text)]
    return pd.DataFrame(rows, columns=["year", "n_districts", *COLS])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", action="append", required=True, metavar="YEAR=PATH")
    args = ap.parse_args()

    pdf = pd.concat([pdf_totals(y, Path(p)) for y, p in (a.split("=", 1) for a in args.pdf)],
                    ignore_index=True)
    data = pd.read_csv(MERGED)
    data = data[data["year"].isin(pdf["year"].unique())]
    g = (data.groupby(["year", "state"])
             .agg(n_districts=("district", "size"), **{c: (c, "sum") for c in COLS})
             .reset_index())

    key = ["year", "n_districts", *COLS]
    m = g.merge(pdf.drop_duplicates(), on=key, how="outer", indicator=True)
    single = m[(m["_merge"] == "left_only") & (m["n_districts"] == 1)]
    data_only = m[(m["_merge"] == "left_only") & (m["n_districts"] > 1)]
    pdf_only = m[m["_merge"] == "right_only"]

    print(f"PDF state totals: {len(pdf)} | data state-years: {len(g)} | "
          f"reconciled: {(m['_merge'] == 'both').sum()}")
    print(f"single-district UTs (no total line, not checkable): "
          f"{sorted(set(single['state']))}")
    ok = True
    if len(pdf_only):
        ok = False
        print("\n[FAIL] totals in the PDF with no matching state-year in the data "
              "(missing state or wrong district values):")
        print(pdf_only[key].to_string(index=False))
    if len(data_only):
        ok = False
        print("\n[FAIL] state-years in the data whose totals match no PDF total line:")
        print(data_only[["state", *key]].to_string(index=False))
    print("\nALL RECONCILED" if ok else "")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
