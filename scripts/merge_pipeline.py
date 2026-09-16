"""
Reusable RHS + LGD + Census population merge pipeline.

Usage:
    python3 merge_pipeline.py --states "Karnataka,Maharashtra,Rajasthan" \
        --rhs rhs_extract.csv --lgd lgd_districts.csv --census census2011_districts.csv \
        --out merged.csv

rhs_extract.csv must have columns: state, district, ... (any count columns), year
The script joins district->LGD code->Census population and writes:
    - <out>: the merged file
    - <out>.review.csv: every non-exact match, for manual review before trusting it
    - prints a coverage summary
"""

import csv, re, difflib, argparse, sys
from collections import defaultdict, Counter

# ---- Growing national crosswalk of known historical district renames ----
# Add to this as each new state's RHS data is pulled and reviewed.
# Format: (state, normalized_old_name): "Correct LGD name"
RENAME_CROSSWALK = {
    ("Karnataka", "belgaum"): "Belagavi",
    ("Karnataka", "bellary"): "Ballari",
    ("Karnataka", "bijapur"): "Vijayapura",
    ("Karnataka", "gulbarga"): "Kalaburagi",
    ("Karnataka", "mysore"): "Mysuru",
    ("Maharashtra", "aurangabad"): "Chhatrapati Sambhajinagar",
    ("Maharashtra", "osmanabad"): "Dharashiv",
    ("Maharashtra", "bid"): "Beed",
    ("Uttar Pradesh", "faizabad"): "Ayodhya",
    ("Uttar Pradesh", "allahabad"): "Prayagraj",
    ("Uttar Pradesh", "c s m nagar"): "Amethi",
    ("Uttar Pradesh", "jyotiba phule nagar"): "Amroha",
    ("Uttar Pradesh", "kashi ram nagar"): "Kasganj",
    ("Uttar Pradesh", "lakhimpur kheri"): "Kheri",
    ("Uttar Pradesh", "maunathbhanjan"): "Mau",
    ("Uttar Pradesh", "sant ravidas nagar"): "Bhadohi",
    ("Tamil Nadu", "tuticorin"): "Thoothukkudi",
    ("Gujarat", "dohad"): "Dahod",
    # Known major renames not yet hit by our pilot states, added as a head start:
    ("Madhya Pradesh", "hoshangabad"): "Narmadapuram",
}


def norm(s):
    s = s.lower().strip()
    s = re.sub(r"[^a-z\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    for junk in [" district"]:
        s = s.replace(junk, "")
    return s.strip()


def norm_code(c):
    c = c.strip()
    if not c:
        return c
    if c.isdigit():
        return str(int(c))  # strips leading zeros safely
    return c


def load_lgd(path, states):
    lgd_by_state = defaultdict(list)
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            st = row["state_name_english"].strip()
            if states and st not in states:
                continue
            code = row["district_census2011_code"].strip()
            name = row["district_name_english"].strip()
            lgd_by_state[st].append((norm(name), name, code))
    return lgd_by_state


def load_population(path):
    pop_by_code = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = norm_code(row["District code"])
            pop_by_code[code] = {
                "population": row["Population"],
                "census_district_name": row["District name"],
            }
    return pop_by_code


def match_district(state, district, lgd_by_state, fuzzy_cutoff=0.75):
    """Returns (matched_code, matched_name, match_type)"""
    ndist = norm(district)
    candidates = lgd_by_state.get(state, [])

    exact = [c for c in candidates if c[0] == ndist]
    if exact:
        return exact[0][2], exact[0][1], "exact"

    if (state, ndist) in RENAME_CROSSWALK:
        target_norm = norm(RENAME_CROSSWALK[(state, ndist)])
        for c in candidates:
            if c[0] == target_norm:
                return c[2], c[1], "crosswalk"

    names = [c[0] for c in candidates]
    close = difflib.get_close_matches(ndist, names, n=1, cutoff=fuzzy_cutoff)
    if close:
        for c in candidates:
            if c[0] == close[0]:
                return c[2], c[1], "fuzzy"

    return None, None, "none"


def run(rhs_path, lgd_path, census_path, out_path, states=None):
    lgd_by_state = load_lgd(lgd_path, states)
    pop_by_code = load_population(census_path)

    with open(rhs_path, encoding="utf-8") as f:
        rhs_rows = list(csv.DictReader(f))

    results = []
    review_rows = []

    for row in rhs_rows:
        st = row["state"].strip()
        dist = row["district"].strip()
        code, matched_name, match_type = match_district(st, dist, lgd_by_state)
        pop_info = pop_by_code.get(norm_code(code)) if code and code != "000" else None

        out = dict(row)
        out["lgd_matched_name"] = matched_name or ""
        out["district_census2011_code"] = code or ""
        out["match_type"] = match_type
        out["population"] = pop_info["population"] if pop_info else ""
        results.append(out)

        if match_type != "exact":
            review_rows.append({
                "state": st, "year": row.get("year", ""), "rhs_district": dist,
                "matched_lgd_name": matched_name or "", "match_type": match_type,
                "district_census2011_code": code or "",
                "population_found": "yes" if pop_info else "no",
            })

    if not results:
        print("No RHS rows found — check input file.")
        sys.exit(1)

    fieldnames = list(results[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(results)

    review_path = out_path.rsplit(".", 1)[0] + ".review.csv"
    if review_rows:
        with open(review_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(review_rows[0].keys()))
            w.writeheader()
            w.writerows(review_rows)

    # ---- Summary ----
    total = len(results)
    counts = Counter(r["match_type"] for r in results)
    has_pop = sum(1 for r in results if r["population"])

    print(f"Total district-year rows: {total}")
    for mtype in ["exact", "crosswalk", "fuzzy", "none"]:
        print(f"  {mtype}: {counts.get(mtype, 0)}")
    print(f"Population coverage: {has_pop}/{total} ({has_pop/total:.1%})")
    if review_rows:
        print(f"\n{len(review_rows)} non-exact matches written to {review_path}")
        print("IMPORTANT: manually review every 'fuzzy' match in that file before trusting it —")
        print("fuzzy matching has produced silent wrong matches before (see DATA_SOURCES.md).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rhs", required=True)
    ap.add_argument("--lgd", required=True)
    ap.add_argument("--census", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--states", default="", help="Comma-separated state list; empty = all states in the RHS file")
    args = ap.parse_args()

    states = set(s.strip() for s in args.states.split(",")) if args.states else None
    run(args.rhs, args.lgd, args.census, args.out, states)
