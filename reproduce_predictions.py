
import joblib
import pandas as pd
import numpy as np

# 1. Load the national temporal dataset
data = pd.read_csv(
    "processed/national_temporal_ml_dataset.csv"
)

# 2. Select the final testing period
test = data[
    (data["year_t"] == "2020-21") &
    (data["year_tp1"] == "2021-22")
].copy()

# 3. Select the five model features
features = [
    "sub_centres_per_100k_t",
    "phcs_per_100k_t",
    "chcs_per_100k_t",
    "sub_divisional_hospital_per_100k_t",
    "district_hospital_per_100k_t"
]

X_test = test[features]

# 4. Load the saved Random Forest model
model = joblib.load("models/random_forest.joblib")

# 5. Generate predictions
predictions = model.predict(X_test)

# 6. Load the original saved predictions
saved = pd.read_csv(
    "results/final_test_predictions.csv"
)

# 7. Compare predictions
print("\n--- REPRODUCIBILITY TEST ---")

print("Test observations:", len(X_test))
print("Saved observations:", len(saved))

print(
    "Predictions match:",
    np.array_equal(
        predictions,
        saved["random_forest_prediction"].to_numpy()
    )
)

print("\nFirst 10 reproduced predictions:")
print(predictions[:10])

print("\nFirst 10 original predictions:")
print(
    saved["random_forest_prediction"].to_numpy()[:10]
)
