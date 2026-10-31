
# Anomaly-handling sensitivity analysis
# Compare:
# 1. Primary analysis: urban and anomalous records excluded
# 2. Sensitivity analysis: urban excluded, anomalies retained
#
# Both scenarios use:
# - Baseline-only Min-Max normalization
# - Equal-weight D-HAI
# - Baseline 25th percentile threshold
# - Chronological ML split
# - Same Random Forest configuration

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

PANEL_PATH = (
    ROOT / "processed" /
    "national_all_years_2011units.csv"
)

PAIRS_PATH = (
    ROOT / "processed" /
    "national_t_to_tplus1_2011units.csv"
)

RESULT_DIR = ROOT / "results"
RESULT_DIR.mkdir(exist_ok=True)

# --------------------------------------------------
# 1. Load datasets
# --------------------------------------------------

panel = pd.read_csv(PANEL_PATH)
pairs_original = pd.read_csv(PAIRS_PATH)

facility_types = [
    "sub_centres",
    "phcs",
    "chcs",
    "sub_divisional_hospital",
    "district_hospital"
]

density_features = [
    f"{name}_per_100k" for name in facility_types
]

# --------------------------------------------------
# 2. Define two scenarios
# --------------------------------------------------

scenarios = {
    "Primary_Exclude_Anomalies": True,
    "Sensitivity_Retain_Anomalies": False
}

all_results = []

# --------------------------------------------------
# 3. Process each scenario
# --------------------------------------------------

for scenario_name, exclude_anomalies in scenarios.items():

    print("\n" + "=" * 65)
    print("SCENARIO:", scenario_name)
    print("=" * 65)

    data = panel.copy()

    # Exclude urban units in both scenarios
    eligible_mask = data["is_urban_unit"] == False

    # Primary scenario additionally excludes anomalies
    if exclude_anomalies:
        eligible_mask &= data["known_anomaly"] == False

    eligible = data[eligible_mask].copy()

    # --------------------------------------------------
    # 4. Fit baseline normalization
    # --------------------------------------------------

    baseline = eligible[
        eligible["year"] == "2019-20"
    ].copy()

    print("Eligible panel records:", len(eligible))
    print("Baseline records:", len(baseline))

    normalization = {}

    for feature in density_features:

        minimum = baseline[feature].min()
        maximum = baseline[feature].max()

        normalization[feature] = {
            "min": minimum,
            "max": maximum
        }

        if maximum == minimum:
            eligible[feature + "_normalized"] = 0.0
        else:
            eligible[feature + "_normalized"] = (
                eligible[feature] - minimum
            ) / (maximum - minimum)

    # --------------------------------------------------
    # 5. Calculate D-HAI
    # --------------------------------------------------

    normalized_features = [
        feature + "_normalized"
        for feature in density_features
    ]

    eligible["D_HAI_national"] = (
        eligible[normalized_features].mean(axis=1)
    )

    # Calculate threshold from baseline only
    baseline_scores = eligible[
        eligible["year"] == "2019-20"
    ]["D_HAI_national"]

    threshold = baseline_scores.quantile(0.25)

    eligible["underserved"] = (
        eligible["D_HAI_national"] <= threshold
    ).astype(int)

    print("Baseline threshold:", round(threshold, 8))

    # --------------------------------------------------
    # 6. Create future-year labels
    # --------------------------------------------------

    labels = eligible[
        ["unit_id", "year", "underserved"]
    ].rename(columns={
        "year": "year_tp1",
        "underserved": "underserved_tp1"
    })

    # Prepare temporal pairs
    pairs = pairs_original.copy()

    # Exclude urban units
    pairs = pairs[
        pairs["is_urban_unit"] == False
    ].copy()

    # Primary scenario excludes anomalies at both endpoints
    if exclude_anomalies:

        pairs = pairs[
            (pairs["known_anomaly_t"] == False) &
            (pairs["known_anomaly_tp1"] == False)
        ].copy()

    # Attach target labels calculated for this scenario
    pairs = pairs.merge(
        labels,
        on=["unit_id", "year_tp1"],
        how="left",
        validate="many_to_one"
    )

    # Remove pairs without a valid future-year label
    pairs = pairs.dropna(
        subset=["underserved_tp1"]
    ).copy()

    # --------------------------------------------------
    # 7. Calculate year-t input features
    # --------------------------------------------------

    for facility in facility_types:

        feature_name = facility + "_per_100k_t"

        pairs[feature_name] = (
            pairs[facility + "_t"] /
            pairs["population"]
        ) * 100000

    features = [
        facility + "_per_100k_t"
        for facility in facility_types
    ]

    # --------------------------------------------------
    # 8. Chronological split
    # --------------------------------------------------

    train = pairs[
        (pairs["year_t"] == "2019-20") &
        (pairs["year_tp1"] == "2020-21")
    ].copy()

    test = pairs[
        (pairs["year_t"] == "2020-21") &
        (pairs["year_tp1"] == "2021-22")
    ].copy()

    X_train = train[features]
    y_train = train["underserved_tp1"].astype(int)

    X_test = test[features]
    y_test = test["underserved_tp1"].astype(int)

    print("Training records:", len(train))
    print("Testing records:", len(test))

    # --------------------------------------------------
    # 9. Train Random Forest
    # --------------------------------------------------

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        max_features="sqrt",
        min_samples_leaf=2,
        class_weight=None,
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]

    # --------------------------------------------------
    # 10. Evaluate
    # --------------------------------------------------

    cm = confusion_matrix(
        y_test,
        predictions,
        labels=[0, 1]
    )

    metrics = {
        "Scenario": scenario_name,
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

    all_results.append(metrics)

    print("\nScenario results:")

    for key, value in metrics.items():
        print(f"{key}: {value}")

# --------------------------------------------------
# 11. Save comparison
# --------------------------------------------------

results_df = pd.DataFrame(all_results)

output_path = (
    RESULT_DIR / "anomaly_sensitivity_results.csv"
)

results_df.to_csv(output_path, index=False)

print("\n" + "=" * 65)
print("FINAL ANOMALY SENSITIVITY COMPARISON")
print("=" * 65)

print(results_df.to_string(index=False))

print("\nSaved results to:")
print(output_path)

print("\nAnomaly sensitivity analysis completed!")
