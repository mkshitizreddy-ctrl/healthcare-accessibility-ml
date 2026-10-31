
# Threshold sensitivity analysis for national D-HAI.
# Tests 20th, 25th and 30th percentile baseline thresholds.
# Uses the same chronological train/test split.
# Random Forest hyperparameters are fixed from the main experiment.

from pathlib import Path
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
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

DHAI_PATH = ROOT / "processed" / "national_dhai_results.csv"
PAIRS_PATH = ROOT / "processed" / "national_t_to_tplus1_2011units.csv"

RESULT_DIR = ROOT / "results"
RESULT_DIR.mkdir(exist_ok=True)

# --------------------------------------------------
# 1. Load data
# --------------------------------------------------

dhai = pd.read_csv(DHAI_PATH)
pairs = pd.read_csv(PAIRS_PATH)

# Use only records with valid D-HAI scores.
# These are the eligible records from the original calculation.
dhai = dhai.dropna(subset=["D_HAI_national"]).copy()

# --------------------------------------------------
# 2. Prepare input features
# --------------------------------------------------

facility_types = [
    "sub_centres",
    "phcs",
    "chcs",
    "sub_divisional_hospital",
    "district_hospital"
]

features = [f"{name}_per_100k_t" for name in facility_types]

for name in facility_types:
    pairs[f"{name}_per_100k_t"] = (
        pairs[f"{name}_t"] / pairs["population"]
    ) * 100000

# --------------------------------------------------
# 3. Define Random Forest configuration
# --------------------------------------------------

rf_parameters = {
    "n_estimators": 300,
    "max_depth": 12,
    "max_features": "sqrt",
    "min_samples_leaf": 2,
    "class_weight": None,
    "random_state": 42,
    "n_jobs": -1
}

percentiles = [20, 25, 30]

results = []

# --------------------------------------------------
# 4. Test each D-HAI threshold
# --------------------------------------------------

for percentile in percentiles:

    print("\n" + "=" * 55)
    print(f"TESTING {percentile}TH PERCENTILE THRESHOLD")
    print("=" * 55)

    # Calculate threshold using eligible baseline records only
    baseline = dhai[dhai["year"] == "2019-20"]

    threshold = baseline["D_HAI_national"].quantile(
        percentile / 100
    )

    print("D-HAI threshold:", round(threshold, 8))

    # Generate labels using the same threshold for all years
    labels = dhai[
        ["unit_id", "year", "D_HAI_national"]
    ].copy()

    labels["underserved"] = (
        labels["D_HAI_national"] <= threshold
    ).astype(int)

    # --------------------------------------------------
    # 5. Attach future-year target labels
    # --------------------------------------------------

    future_labels = labels[
        ["unit_id", "year", "underserved"]
    ].rename(columns={
        "year": "year_tp1",
        "underserved": "underserved_tp1"
    })

    data = pairs.merge(
        future_labels,
        on=["unit_id", "year_tp1"],
        how="left",
        validate="many_to_one"
    )

    # Exclude urban and anomalous transitions
    data = data[
        (data["is_urban_unit"] == False) &
        (data["known_anomaly_t"] == False) &
        (data["known_anomaly_tp1"] == False)
    ].dropna(subset=["underserved_tp1"]).copy()

    # --------------------------------------------------
    # 6. Chronological train/test split
    # --------------------------------------------------

    train = data[
        (data["year_t"] == "2019-20") &
        (data["year_tp1"] == "2020-21")
    ]

    test = data[
        (data["year_t"] == "2020-21") &
        (data["year_tp1"] == "2021-22")
    ]

    X_train = train[features]
    y_train = train["underserved_tp1"].astype(int)

    X_test = test[features]
    y_test = test["underserved_tp1"].astype(int)

    print("Training records:", len(train))
    print("Testing records:", len(test))

    print("Training target counts:")
    print(y_train.value_counts().sort_index().to_dict())

    print("Testing target counts:")
    print(y_test.value_counts().sort_index().to_dict())

    # --------------------------------------------------
    # 7. Train Random Forest
    # --------------------------------------------------

    model = RandomForestClassifier(**rf_parameters)

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]

    # --------------------------------------------------
    # 8. Evaluate model
    # --------------------------------------------------

    cm = confusion_matrix(
        y_test,
        predictions,
        labels=[0, 1]
    )

    metrics = {
        "Percentile": percentile,
        "Threshold": threshold,
        "Train_records": len(train),
        "Test_records": len(test),
        "Test_underserved": int(y_test.sum()),
        "Accuracy": accuracy_score(y_test, predictions),
        "Precision": precision_score(
            y_test, predictions, zero_division=0
        ),
        "Recall": recall_score(
            y_test, predictions, zero_division=0
        ),
        "F1_Score": f1_score(
            y_test, predictions, zero_division=0
        ),
        "PR_AUC": average_precision_score(
            y_test, probabilities
        ),
        "ROC_AUC": roc_auc_score(
            y_test, probabilities
        ),
        "TN": int(cm[0, 0]),
        "FP": int(cm[0, 1]),
        "FN": int(cm[1, 0]),
        "TP": int(cm[1, 1])
    }

    results.append(metrics)

    print("\nTest results:")
    for metric, value in metrics.items():
        if metric not in ["Percentile", "Threshold"]:
            print(f"{metric}: {value}")

# --------------------------------------------------
# 9. Save comparison
# --------------------------------------------------

results_df = pd.DataFrame(results)

output_path = RESULT_DIR / "threshold_sensitivity_results.csv"

results_df.to_csv(output_path, index=False)

print("\n" + "=" * 55)
print("THRESHOLD SENSITIVITY COMPARISON")
print("=" * 55)

print(results_df.to_string(index=False))

print("\nSaved results to:")
print(output_path)

print("\nThreshold sensitivity analysis completed!")
