
# Import pandas for inspecting the national D-HAI results
import pandas as pd

# Import NumPy for checking numerical conditions
import numpy as np

# Load the calculated national D-HAI dataset
df = pd.read_csv("processed/national_dhai_results.csv")

# List the five normalized healthcare indicators
features = [
    "sub_centres_normalized",
    "phcs_normalized",
    "chcs_normalized",
    "sub_divisional_hospital_normalized",
    "district_hospital_normalized",
]

# Keep only records that received a D-HAI score
valid = df[df["D_HAI_national"].notna()].copy()

# Display the number of valid records
print("\n--- VALIDATION SUMMARY ---")
print("Valid records:", len(valid))

# Check values outside the baseline normalization range
print("\n--- NORMALIZED VALUES OUTSIDE 0 TO 1 ---")

for feature in features:
    below_zero = (valid[feature] < 0).sum()
    above_one = (valid[feature] > 1).sum()

    print(f"\n{feature}")
    print("Below zero:", below_zero)
    print("Above one:", above_one)

# Display D-HAI distribution by year
print("\n--- D-HAI BY YEAR ---")
print(valid.groupby("year")["D_HAI_national"].describe())

# Check underserved label distribution
print("\n--- TARGET DISTRIBUTION ---")
print(valid["underserved"].value_counts())

# Check missing values in important output columns
print("\n--- MISSING VALUES ---")
print(valid[features + ["D_HAI_national", "underserved"]].isna().sum())

# Check whether the D-HAI score matches the average
# of the five normalized indicators
recalculated = valid[features].mean(axis=1)

difference = (
    valid["D_HAI_national"] - recalculated
).abs().max()

print("\n--- FORMULA VALIDATION ---")
print("Maximum D-HAI calculation difference:", difference)

# Check whether all eligible labels are binary
print("\n--- LABEL VALIDATION ---")
print("Unique labels:", sorted(valid["underserved"].unique()))

print("\nNational D-HAI validation completed!")
