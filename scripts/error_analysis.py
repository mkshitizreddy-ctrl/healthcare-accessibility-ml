
# Error analysis for the trained Random Forest model
# Identifies correctly and incorrectly classified units.

from pathlib import Path
import joblib
import pandas as pd

from sklearn.metrics import confusion_matrix

ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = ROOT / "processed" / "national_temporal_ml_dataset.csv"
MODEL_PATH = ROOT / "models" / "random_forest.joblib"
RESULT_DIR = ROOT / "results"

RESULT_DIR.mkdir(exist_ok=True)

# Load dataset
data = pd.read_csv(DATA_PATH)

# Select chronological test period
test = data[
    (data["year_t"] == "2020-21") &
    (data["year_tp1"] == "2021-22")
].copy()

# Select model features
features = [
    "sub_centres_per_100k_t",
    "phcs_per_100k_t",
    "chcs_per_100k_t",
    "sub_divisional_hospital_per_100k_t",
    "district_hospital_per_100k_t"
]

X_test = test[features]
y_test = test["underserved_tp1"].astype(int)

# Load trained model
pipeline = joblib.load(MODEL_PATH)

# Generate predictions
predictions = pipeline.predict(X_test)
probabilities = pipeline.predict_proba(X_test)[:, 1]

# Add predictions to test data
test["predicted_status"] = predictions
test["predicted_probability"] = probabilities
test["actual_status"] = y_test

# Categorise predictions
def classify_result(row):

    if row["actual_status"] == 1 and row["predicted_status"] == 1:
        return "True Positive"

    elif row["actual_status"] == 0 and row["predicted_status"] == 0:
        return "True Negative"

    elif row["actual_status"] == 0 and row["predicted_status"] == 1:
        return "False Positive"

    else:
        return "False Negative"


test["prediction_result"] = test.apply(
    classify_result,
    axis=1
)

# Display confusion matrix
cm = confusion_matrix(
    y_test,
    predictions,
    labels=[0, 1]
)

print("--- CONFUSION MATRIX ---")
print(cm)

print("\n--- ERROR COUNTS ---")
print(test["prediction_result"].value_counts())

# Select useful columns
output_columns = [
    "unit_id",
    "state",
    "unit_name",
    "year_t",
    "year_tp1",
    "actual_status",
    "predicted_status",
    "predicted_probability",
    "prediction_result"
] + features

# Save all predictions
test[output_columns].to_csv(
    RESULT_DIR / "national_error_analysis_all.csv",
    index=False
)

# Save only incorrect predictions
errors = test[
    test["actual_status"] != test["predicted_status"]
]

errors[output_columns].to_csv(
    RESULT_DIR / "national_misclassified_units.csv",
    index=False
)

# Display false negatives
false_negatives = test[
    test["prediction_result"] == "False Negative"
]

print("\n--- FALSE NEGATIVES ---")
print(
    false_negatives[output_columns].to_string(index=False)
)

# Display false positives
false_positives = test[
    test["prediction_result"] == "False Positive"
]

print("\n--- FALSE POSITIVES ---")
print(
    false_positives[output_columns].to_string(index=False)
)

print("\nError analysis completed.")
print("Saved all predictions and misclassified units in results/")
