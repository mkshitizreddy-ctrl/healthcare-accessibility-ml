
# Validate chronological training and testing datasets

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

INPUT_PATH = ROOT / "processed" / "national_temporal_ml_dataset.csv"

data = pd.read_csv(INPUT_PATH)

# Split strictly by time
train = data[
    (data["year_t"] == "2019-20") &
    (data["year_tp1"] == "2020-21")
].copy()

test = data[
    (data["year_t"] == "2020-21") &
    (data["year_tp1"] == "2021-22")
].copy()

# Separate input features and target
features = [
    "sub_centres_per_100k_t",
    "phcs_per_100k_t",
    "chcs_per_100k_t",
    "sub_divisional_hospital_per_100k_t",
    "district_hospital_per_100k_t"
]

target = "underserved_tp1"

X_train = train[features]
y_train = train[target]

X_test = test[features]
y_test = test[target]

# Display split information
print("--- CHRONOLOGICAL SPLIT ---")

print("\nTraining period:")
print("2019-20 -> 2020-21")

print("Training shape:", X_train.shape)
print("Training target distribution:")
print(y_train.value_counts().sort_index())

print("\nTesting period:")
print("2020-21 -> 2021-22")

print("Testing shape:", X_test.shape)
print("Testing target distribution:")
print(y_test.value_counts().sort_index())

# Check for missing values
print("\n--- MISSING VALUE CHECK ---")
print("Training:", X_train.isnull().sum().sum())
print("Testing:", X_test.isnull().sum().sum())

# Verify chronological ordering
assert train["year_t"].nunique() == 1
assert test["year_t"].nunique() == 1
assert len(train) == 600
assert len(test) == 601

print("\nChronological split validated successfully!")
