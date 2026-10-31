
# Prepare the national temporal dataset for ML
# Input: facility data at year t
# Target: underserved status at year t+1

from pathlib import Path
import pandas as pd

# --------------------------------------------------
# 1. Project paths
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

PAIRS_PATH = ROOT / "processed" / "national_t_to_tplus1_2011units.csv"
DHAI_PATH = ROOT / "processed" / "national_dhai_results.csv"

OUTPUT_PATH = ROOT / "processed" / "national_temporal_ml_dataset.csv"

# --------------------------------------------------
# 2. Load datasets
# --------------------------------------------------

pairs = pd.read_csv(PAIRS_PATH)
dhai = pd.read_csv(DHAI_PATH)

print("Temporal pairs shape:", pairs.shape)
print("D-HAI results shape:", dhai.shape)

# --------------------------------------------------
# 3. Prepare target labels from the D-HAI dataset
# --------------------------------------------------

labels = dhai[
    ["unit_id", "year", "underserved"]
].copy()

# Rename year to match the following year in temporal pairs
labels = labels.rename(columns={
    "year": "year_tp1",
    "underserved": "underserved_tp1"
})

# --------------------------------------------------
# 4. Join future-year labels to temporal pairs
# --------------------------------------------------

data = pairs.merge(
    labels,
    on=["unit_id", "year_tp1"],
    how="left",
    validate="many_to_one"
)

# --------------------------------------------------
# 5. Exclude urban and anomalous observations
# --------------------------------------------------

data = data[
    (data["is_urban_unit"] == False) &
    (data["known_anomaly_t"] == False) &
    (data["known_anomaly_tp1"] == False)
].copy()

# Remove records without a valid future-year target
data = data.dropna(subset=["underserved_tp1"])

# --------------------------------------------------
# 6. Calculate facility density using year-t counts
# --------------------------------------------------

facility_types = [
    "sub_centres",
    "phcs",
    "chcs",
    "sub_divisional_hospital",
    "district_hospital"
]

feature_columns = []

for facility in facility_types:

    feature_name = facility + "_per_100k_t"

    data[feature_name] = (
        data[facility + "_t"] /
        data["population"]
    ) * 100000

    feature_columns.append(feature_name)

# --------------------------------------------------
# 7. Prepare final ML dataset
# --------------------------------------------------

target_column = "underserved_tp1"

final_columns = [
    "unit_id",
    "state",
    "unit_name",
    "year_t",
    "year_tp1"
] + feature_columns + [target_column]

ml_data = data[final_columns].copy()

# Ensure target is integer
ml_data[target_column] = ml_data[target_column].astype(int)

# --------------------------------------------------
# 8. Validate the dataset
# --------------------------------------------------

print("\n--- FINAL DATASET ---")
print("Shape:", ml_data.shape)

print("\n--- TRANSITION COUNTS ---")
print(ml_data.groupby(
    ["year_t", "year_tp1"]
).size())

print("\n--- TARGET DISTRIBUTION ---")
print(ml_data[target_column].value_counts())

print("\n--- MISSING VALUES ---")
print(ml_data.isnull().sum())

print("\n--- DUPLICATE CHECK ---")
print(
    "Duplicate unit-transition rows:",
    ml_data.duplicated(
        subset=["unit_id", "year_t", "year_tp1"]
    ).sum()
)

# Check expected total
expected_records = 1201

if len(ml_data) != expected_records:
    print(
        f"\nWARNING: Expected {expected_records} records, "
        f"but obtained {len(ml_data)}."
    )
else:
    print("\nExpected record count verified!")

# --------------------------------------------------
# 9. Save dataset
# --------------------------------------------------

ml_data.to_csv(OUTPUT_PATH, index=False)

print("\nTemporal ML dataset saved to:")
print(OUTPUT_PATH)
