
# Compare ML models against a simple persistence baseline.
# Persistence assumption:
# A unit keeps its previous year's underserved status.

from pathlib import Path
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    roc_auc_score,
    confusion_matrix
)

ROOT = Path(__file__).resolve().parents[1]

ML_PATH = ROOT / "processed" / "national_temporal_ml_dataset.csv"
DHAI_PATH = ROOT / "processed" / "national_dhai_results.csv"

# Load datasets
ml_data = pd.read_csv(ML_PATH)
dhai = pd.read_csv(DHAI_PATH)

# Obtain previous-year underserved labels
previous_labels = dhai[
    ["unit_id", "year", "underserved"]
].rename(columns={
    "year": "year_t",
    "underserved": "underserved_t"
})

# Obtain test transition only
test = ml_data[
    (ml_data["year_t"] == "2020-21") &
    (ml_data["year_tp1"] == "2021-22")
].copy()

# Attach previous-year labels
test = test.merge(
    previous_labels,
    on=["unit_id", "year_t"],
    how="left",
    validate="one_to_one"
)

# Validate labels
assert test["underserved_t"].notna().all()

y_true = test["underserved_tp1"].astype(int)
y_pred = test["underserved_t"].astype(int)

# Calculate metrics
print("--- PERSISTENCE BASELINE ---")

print("Records:", len(test))
print("Accuracy:", round(accuracy_score(y_true, y_pred), 4))
print("Precision:", round(
    precision_score(y_true, y_pred, zero_division=0), 4
))
print("Recall:", round(
    recall_score(y_true, y_pred, zero_division=0), 4
))
print("F1-score:", round(
    f1_score(y_true, y_pred, zero_division=0), 4
))

# Previous-year binary label used as a score for ranking
print("PR-AUC:", round(
    average_precision_score(y_true, y_pred), 4
))
print("ROC-AUC:", round(
    roc_auc_score(y_true, y_pred), 4
))

print("\nConfusion matrix:")
print(confusion_matrix(y_true, y_pred, labels=[0, 1]))

print("\nPersistence baseline evaluation completed.")
