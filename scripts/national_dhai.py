
# ============================================================
# NATIONAL D-HAI CALCULATION
# Project: Healthcare Accessibility Assessment
# ============================================================

# Import required libraries
import json
from pathlib import Path

import numpy as np
import pandas as pd


# ------------------------------------------------------------
# 1. Define project paths
# ------------------------------------------------------------

# Find the main project directory automatically
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Input national dataset
INPUT_FILE = PROJECT_ROOT / "processed" / "national_all_years_2011units.csv"

# Output files
OUTPUT_FILE = PROJECT_ROOT / "processed" / "national_dhai_results.csv"
METADATA_FILE = PROJECT_ROOT / "processed" / "national_dhai_metadata.json"


# ------------------------------------------------------------
# 2. Define D-HAI configuration
# ------------------------------------------------------------

# Baseline year used for normalization and threshold calculation
BASELINE_YEAR = "2019-20"

# Percentile used to define the underserved threshold
THRESHOLD_PERCENTILE = 25

# Five healthcare facility-density indicators
FEATURES = [
    "sub_centres_per_100k",
    "phcs_per_100k",
    "chcs_per_100k",
    "sub_divisional_hospital_per_100k",
    "district_hospital_per_100k",
]

# Raw facility-count columns used for validation
RAW_FEATURES = [
    "sub_centres",
    "phcs",
    "chcs",
    "sub_divisional_hospital",
    "district_hospital",
]


# ------------------------------------------------------------
# 3. Load the national dataset
# ------------------------------------------------------------

print("\n========== NATIONAL D-HAI CALCULATION ==========")

# Check whether the input file exists
if not INPUT_FILE.exists():
    raise FileNotFoundError(f"Dataset not found: {INPUT_FILE}")

# Load the national panel
df = pd.read_csv(INPUT_FILE)

print("Original dataset shape:", df.shape)


# ------------------------------------------------------------
# 4. Validate required columns
# ------------------------------------------------------------

# List all columns required by this calculation
required_columns = [
    "unit_id",
    "unit_name",
    "state",
    "year",
    "population",
    "is_urban_unit",
    "known_anomaly",
] + FEATURES + RAW_FEATURES

# Stop execution if any required column is missing
missing_columns = [
    column for column in required_columns
    if column not in df.columns
]

if missing_columns:
    raise ValueError(f"Missing required columns: {missing_columns}")


# ------------------------------------------------------------
# 5. Prepare flags and numerical columns
# ------------------------------------------------------------

# Convert urban flags into reliable Boolean values
df["is_urban_unit"] = (
    df["is_urban_unit"]
    .astype(str)
    .str.strip()
    .str.lower()
    .isin(["true", "1", "yes"])
)

# Convert anomaly flags into reliable Boolean values
df["known_anomaly"] = (
    df["known_anomaly"]
    .astype(str)
    .str.strip()
    .str.lower()
    .isin(["true", "1", "yes"])
)

# Convert population, raw counts and density features to numbers
numeric_columns = ["population"] + RAW_FEATURES + FEATURES

for column in numeric_columns:
    df[column] = pd.to_numeric(df[column], errors="coerce")

# Check for missing population
if df["population"].isna().any():
    raise ValueError("Missing population values detected.")

# Population must be positive
if (df["population"] <= 0).any():
    raise ValueError("Zero or negative population detected.")

# Check for missing facility-density values
if df[FEATURES].isna().any().any():
    raise ValueError("Missing facility-density values detected.")


# ------------------------------------------------------------
# 6. Validate the supplied per-100k indicators
# ------------------------------------------------------------

print("\n========== FACILITY DENSITY VALIDATION ==========")

# Recalculate facility densities from raw counts and population
for raw_column, density_column in zip(RAW_FEATURES, FEATURES):

    # Calculate facilities per 100,000 people
    calculated_density = (
        df[raw_column] / df["population"]
    ) * 100000

    # Calculate the largest difference from the supplied column
    max_difference = (
        calculated_density - df[density_column]
    ).abs().max()

    print(f"{density_column}: maximum difference = {max_difference:.8f}")


# ------------------------------------------------------------
# 7. Identify eligible observations
# ------------------------------------------------------------

print("\n========== DATA QUALITY FILTERING ==========")

# Exclude urban units because RHS counts rural facilities
urban_mask = df["is_urban_unit"]

# Exclude records flagged with known source anomalies
anomaly_mask = df["known_anomaly"]

# Eligible records must be neither urban nor anomalous
eligible_mask = ~(urban_mask | anomaly_mask)

# Select eligible baseline observations
baseline_mask = (
    eligible_mask &
    (df["year"].astype(str) == BASELINE_YEAR)
)

print("Total records:", len(df))
print("Urban records:", int(urban_mask.sum()))
print("Anomalous records:", int(anomaly_mask.sum()))
print("Records excluded:", int((~eligible_mask).sum()))
print("Eligible records:", int(eligible_mask.sum()))
print("Eligible baseline records:", int(baseline_mask.sum()))

# Ensure that baseline observations are available
if baseline_mask.sum() == 0:
    raise ValueError("No eligible baseline observations found.")


# ------------------------------------------------------------
# 8. Calculate baseline normalization parameters
# ------------------------------------------------------------

print("\n========== BASELINE NORMALIZATION ==========")

# Store the minimum and maximum values for each feature
normalization_parameters = {}

for feature in FEATURES:

    # Calculate minimum using eligible baseline observations only
    baseline_min = df.loc[baseline_mask, feature].min()

    # Calculate maximum using eligible baseline observations only
    baseline_max = df.loc[baseline_mask, feature].max()

    # Avoid division by zero
    if baseline_max == baseline_min:
        raise ValueError(
            f"Feature {feature} has identical baseline minimum "
            "and maximum values."
        )

    # Save the baseline parameters
    normalization_parameters[feature] = {
        "minimum": float(baseline_min),
        "maximum": float(baseline_max),
    }

    print(
        f"{feature}: min={baseline_min:.6f}, "
        f"max={baseline_max:.6f}"
    )


# ------------------------------------------------------------
# 9. Apply fixed baseline Min-Max normalization
# ------------------------------------------------------------

# Create a copy of the original dataset
result = df.copy()

# Initialize normalized feature columns with missing values
normalized_columns = []

for feature in FEATURES:

    normalized_feature = feature.replace(
        "_per_100k", "_normalized"
    )

    normalized_columns.append(normalized_feature)

    # Read baseline minimum and maximum
    minimum = normalization_parameters[feature]["minimum"]
    maximum = normalization_parameters[feature]["maximum"]

    # Apply the same baseline scaling to eligible observations
    result[normalized_feature] = np.nan

    result.loc[eligible_mask, normalized_feature] = (
        (result.loc[eligible_mask, feature] - minimum)
        / (maximum - minimum)
    )


# ------------------------------------------------------------
# 10. Calculate D-HAI
# ------------------------------------------------------------

# Initialize D-HAI for all records
result["D_HAI_national"] = np.nan

# Calculate the equal-weight average of five normalized indicators
result.loc[eligible_mask, "D_HAI_national"] = (
    result.loc[eligible_mask, normalized_columns]
    .mean(axis=1)
)

print("\n========== D-HAI SUMMARY ==========")

# Display descriptive statistics for eligible records
print(
    result.loc[eligible_mask, "D_HAI_national"]
    .describe()
)


# ------------------------------------------------------------
# 11. Calculate the underserved threshold
# ------------------------------------------------------------

# Use only eligible baseline D-HAI values
baseline_scores = result.loc[
    baseline_mask, "D_HAI_national"
]

# Calculate the 25th-percentile baseline threshold
threshold = baseline_scores.quantile(
    THRESHOLD_PERCENTILE / 100
)

print("\n========== UNDERSERVED THRESHOLD ==========")

print(
    f"Baseline year: {BASELINE_YEAR}"
)

print(
    f"Threshold percentile: {THRESHOLD_PERCENTILE}"
)

print(
    f"D-HAI threshold: {threshold:.8f}"
)


# ------------------------------------------------------------
# 12. Create underserved labels
# ------------------------------------------------------------

# Initialize target labels as missing
result["underserved"] = pd.Series(
    pd.NA,
    index=result.index,
    dtype="Int64"
)

# A score at or below the threshold is labelled underserved
result.loc[
    eligible_mask & (result["D_HAI_national"] <= threshold),
    "underserved"
] = 1

# A score above the threshold is labelled not underserved
result.loc[
    eligible_mask & (result["D_HAI_national"] > threshold),
    "underserved"
] = 0


# ------------------------------------------------------------
# 13. Display target distribution
# ------------------------------------------------------------

print("\n========== UNDERSERVED DISTRIBUTION ==========")

print(
    result.loc[eligible_mask, "underserved"]
    .value_counts()
    .sort_index()
)

print("\nYear-wise underserved distribution:")

print(
    result.loc[eligible_mask]
    .groupby("year")["underserved"]
    .value_counts()
    .sort_index()
)


# ------------------------------------------------------------
# 14. Save national D-HAI results
# ------------------------------------------------------------

# Save all original rows, retaining excluded rows with missing scores
result.to_csv(OUTPUT_FILE, index=False)

print("\nSaved D-HAI results to:")
print(OUTPUT_FILE)


# ------------------------------------------------------------
# 15. Save methodology and normalization metadata
# ------------------------------------------------------------

metadata = {
    "project": "National District Healthcare Accessibility Index",
    "baseline_year": BASELINE_YEAR,
    "threshold_percentile": THRESHOLD_PERCENTILE,
    "threshold_value": float(threshold),
    "eligible_baseline_records": int(baseline_mask.sum()),
    "total_records": int(len(df)),
    "eligible_records": int(eligible_mask.sum()),
    "urban_records_excluded": int(urban_mask.sum()),
    "anomaly_records_excluded": int(anomaly_mask.sum()),
    "normalization_method": "Baseline Min-Max normalization",
    "aggregation_method": "Equal-weight arithmetic mean",
    "features": FEATURES,
    "normalization_parameters": normalization_parameters,
    "label_definition": {
        "underserved": "D-HAI <= baseline threshold",
        "not_underserved": "D-HAI > baseline threshold",
    },
}

# Write metadata as a JSON file
with open(METADATA_FILE, "w", encoding="utf-8") as file:
    json.dump(metadata, file, indent=4)

print("\nSaved methodology metadata to:")
print(METADATA_FILE)


# ------------------------------------------------------------
# 16. Final summary
# ------------------------------------------------------------

print("\n========== FINAL SUMMARY ==========")

print("Original records:", len(df))
print("Eligible records:", int(eligible_mask.sum()))
print("Baseline records:", int(baseline_mask.sum()))
print("Urban records excluded:", int(urban_mask.sum()))
print("Anomaly records excluded:", int(anomaly_mask.sum()))
print("D-HAI threshold:", round(float(threshold), 8))

print("\nNational D-HAI calculation completed successfully!")
