
"""
Population Denominator Sensitivity Analysis
National Healthcare Accessibility Project

Compare:
1. Primary model: Census-2011 population denominator.
2. Sensitivity model: Harvard 2020 population denominator.

Two population samples:
A. All mapped units.
B. Only units flagged as plausible.

The original dataset, models and results are not overwritten.
"""

from pathlib import Path
import json

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix
)

# --------------------------------------------------
# 1. Paths and configuration
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

PAIRS_PATH = ROOT / "processed" / "national_t_to_tplus1_2011units.csv"
DHAI_PATH = ROOT / "processed" / "national_dhai_results.csv"
POP_PATH = ROOT / "processed" / "unit_population_2020.csv"

OUT_DIR = ROOT / "results" / "population_sensitivity"
MODEL_DIR = ROOT / "models" / "population_sensitivity"

OUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

FACILITIES = [
    "sub_centres",
    "phcs",
    "chcs",
    "sub_divisional_hospital",
    "district_hospital"
]

FEATURES_2011 = [f"{f}_per_100k_2011pop" for f in FACILITIES]
FEATURES_2020 = [f"{f}_per_100k_2020pop" for f in FACILITIES]

TARGET = "underserved_tp1"

# Same tuning setup as the primary Random Forest experiment
PARAM_GRID = {
    "model__max_depth": [5, 8, 12, None],
    "model__min_samples_leaf": [2, 5, 10],
    "model__max_features": ["sqrt", None],
    "model__class_weight": [None, "balanced"]
}

CV = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)


# --------------------------------------------------
# 2. Load data
# --------------------------------------------------

print("=" * 65)
print("POPULATION DENOMINATOR SENSITIVITY ANALYSIS")
print("=" * 65)

pairs = pd.read_csv(PAIRS_PATH)
dhai = pd.read_csv(DHAI_PATH)
population = pd.read_csv(POP_PATH)

print("\nLoaded temporal pairs:", pairs.shape)
print("Loaded D-HAI results:", dhai.shape)
print("Loaded population data:", population.shape)


# --------------------------------------------------
# 3. Prepare future-year target labels
# --------------------------------------------------

labels = dhai[
    ["unit_id", "year", "underserved"]
].copy()

labels = labels.rename(columns={
    "year": "year_tp1",
    "underserved": TARGET
})

data = pairs.merge(
    labels,
    on=["unit_id", "year_tp1"],
    how="left",
    validate="many_to_one"
)

# Match the primary dataset's exclusion rules
data = data[
    (data["is_urban_unit"] == False) &
    (data["known_anomaly_t"] == False) &
    (data["known_anomaly_tp1"] == False)
].copy()

data = data.dropna(subset=[TARGET])
data[TARGET] = data[TARGET].astype(int)


# --------------------------------------------------
# 4. Merge Harvard population
# --------------------------------------------------

population = population[
    [
        "unit_id",
        "population_2020",
        "pop2020_plausible"
    ]
].copy()

if population["unit_id"].duplicated().any():
    raise ValueError("Duplicate unit IDs in population data.")

data = data.merge(
    population,
    on="unit_id",
    how="left",
    validate="many_to_one",
    indicator=True
)

if not (data["_merge"] == "both").all():
    missing = data.loc[
        data["_merge"] != "both", "unit_id"
    ].unique()
    raise ValueError(f"Missing population mapping: {missing}")

data = data.drop(columns="_merge")

if data["population_2020"].isna().any():
    raise ValueError("Missing 2020 population values found.")

if (data["population_2020"] <= 0).any():
    raise ValueError("Non-positive 2020 population values found.")


# --------------------------------------------------
# 5. Calculate both sets of features
# --------------------------------------------------

for facility in FACILITIES:

    data[f"{facility}_per_100k_2011pop"] = (
        data[facility + "_t"] /
        data["population"]
    ) * 100000

    data[f"{facility}_per_100k_2020pop"] = (
        data[facility + "_t"] /
        data["population_2020"]
    ) * 100000

# Save constructed sensitivity dataset
data.to_csv(
    OUT_DIR / "population_sensitivity_dataset.csv",
    index=False
)

print("\nPrepared sensitivity dataset:", data.shape)


# --------------------------------------------------
# 6. Define the chronological train/test split
# --------------------------------------------------

def split_data(df, features):

    train = df[
        (df["year_t"] == "2019-20") &
        (df["year_tp1"] == "2020-21")
    ].copy()

    test = df[
        (df["year_t"] == "2020-21") &
        (df["year_tp1"] == "2021-22")
    ].copy()

    X_train = train[features]
    y_train = train[TARGET]

    X_test = test[features]
    y_test = test[TARGET]

    if X_train.isna().any().any() or X_test.isna().any().any():
        raise ValueError("Missing feature values detected.")

    return X_train, y_train, X_test, y_test


# --------------------------------------------------
# 7. Train and evaluate Random Forest
# --------------------------------------------------

def evaluate_experiment(df, feature_set, sample_name, denominator):

    features = FEATURES_2011 if denominator == "2011" else FEATURES_2020

    X_train, y_train, X_test, y_test = split_data(
        df, features
    )

    pipeline = Pipeline([
        ("model", RandomForestClassifier(
            n_estimators=300,
            random_state=42,
            n_jobs=-1
        ))
    ])

    search = GridSearchCV(
        estimator=pipeline,
        param_grid=PARAM_GRID,
        scoring="average_precision",
        cv=CV,
        n_jobs=-1,
        refit=True,
        verbose=0
    )

    search.fit(X_train, y_train)

    best_model = search.best_estimator_

    predictions = best_model.predict(X_test)
    probabilities = best_model.predict_proba(X_test)[:, 1]

    cm = confusion_matrix(
        y_test, predictions, labels=[0, 1]
    )

    metrics = {
        "Sample": sample_name,
        "Denominator": denominator,
        "Features": feature_set,
        "Train_records": len(X_train),
        "Test_records": len(X_test),
        "Test_underserved": int(y_test.sum()),
        "CV_PR_AUC": search.best_score_,
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
        "ROC_AUC": roc_auc_score(y_test, probabilities),
        "PR_AUC": average_precision_score(y_test, probabilities),
        "Balanced_Accuracy": balanced_accuracy_score(
            y_test, predictions
        ),
        "TN": int(cm[0, 0]),
        "FP": int(cm[0, 1]),
        "FN": int(cm[1, 0]),
        "TP": int(cm[1, 1])
    }

    # Save models separately
    model_name = f"{sample_name}_{denominator}_random_forest.joblib"

    joblib.dump(
        best_model,
        MODEL_DIR / model_name
    )

    metrics["Best_parameters"] = json.dumps(
        search.best_params_
    )

    print(
        f"\n{sample_name} | {denominator} population denominator"
    )
    print("Train:", len(X_train), "| Test:", len(X_test))
    print("Best CV PR-AUC:", round(search.best_score_, 4))
    print("Test F1:", round(metrics["F1_Score"], 4))
    print("Test PR-AUC:", round(metrics["PR_AUC"], 4))
    print("Test ROC-AUC:", round(metrics["ROC_AUC"], 4))
    print("Confusion matrix:\n", cm)

    return metrics


# --------------------------------------------------
# 8. Run all four experiments
# --------------------------------------------------

experiments = []

samples = {
    "all_units": data.copy(),
    "plausible_units": data[
        data["pop2020_plausible"] == True
    ].copy()
}

for sample_name, sample_data in samples.items():

    print("\n" + "=" * 65)
    print("SAMPLE:", sample_name)
    print("Records:", len(sample_data))
    print("Unique units:", sample_data["unit_id"].nunique())

    for denominator in ["2011", "2020"]:

        result = evaluate_experiment(
            sample_data,
            feature_set="five_facility_features",
            sample_name=sample_name,
            denominator=denominator
        )

        experiments.append(result)


# --------------------------------------------------
# 9. Save results
# --------------------------------------------------

results = pd.DataFrame(experiments)

results.to_csv(
    OUT_DIR / "population_sensitivity_comparison.csv",
    index=False
)

# Create an easier comparison table
comparison = results[
    [
        "Sample",
        "Denominator",
        "Train_records",
        "Test_records",
        "CV_PR_AUC",
        "Accuracy",
        "Precision",
        "Recall",
        "F1_Score",
        "ROC_AUC",
        "PR_AUC",
        "Balanced_Accuracy"
    ]
].copy()

comparison.to_csv(
    OUT_DIR / "population_sensitivity_summary.csv",
    index=False
)

print("\n" + "=" * 65)
print("FINAL POPULATION SENSITIVITY COMPARISON")
print("=" * 65)

print(comparison.round(4).to_string(index=False))

print("\nSaved outputs:")
print(OUT_DIR)
print(MODEL_DIR)

print("\nPopulation sensitivity experiment completed.")
