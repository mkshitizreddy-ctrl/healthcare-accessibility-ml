
# National Healthcare Accessibility Project
# Train and compare three ML approaches:
# 1. Logistic Regression
# 2. Decision Tree
# 3. Random Forest
#
# Hyperparameter tuning uses training data only.
# The test set is evaluated only after tuning.

from pathlib import Path
import json

import joblib
import pandas as pd

from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    classification_report
)

# --------------------------------------------------
# 1. Paths
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = ROOT / "processed" / "national_temporal_ml_dataset.csv"

MODEL_DIR = ROOT / "models"
RESULT_DIR = ROOT / "results"

MODEL_DIR.mkdir(exist_ok=True)
RESULT_DIR.mkdir(exist_ok=True)

# --------------------------------------------------
# 2. Load and split data chronologically
# --------------------------------------------------

data = pd.read_csv(DATA_PATH)

train = data[
    (data["year_t"] == "2019-20") &
    (data["year_tp1"] == "2020-21")
].copy()

test = data[
    (data["year_t"] == "2020-21") &
    (data["year_tp1"] == "2021-22")
].copy()

features = [
    "sub_centres_per_100k_t",
    "phcs_per_100k_t",
    "chcs_per_100k_t",
    "sub_divisional_hospital_per_100k_t",
    "district_hospital_per_100k_t"
]

target = "underserved_tp1"

X_train = train[features]
y_train = train[target].astype(int)

X_test = test[features]
y_test = test[target].astype(int)

print("Training records:", len(X_train))
print("Testing records:", len(X_test))

# --------------------------------------------------
# 3. Define cross-validation
# --------------------------------------------------

cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)

# --------------------------------------------------
# 4. Define models and hyperparameter grids
# --------------------------------------------------

models = {

    "Logistic Regression": {

        "pipeline": Pipeline([
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(
                max_iter=3000,
                random_state=42
            ))
        ]),

        "params": {
            "model__C": [0.01, 0.1, 1, 10, 100],
            "model__class_weight": [None, "balanced"]
        }
    },

    "Decision Tree": {

        "pipeline": Pipeline([
            ("model", DecisionTreeClassifier(
                random_state=42
            ))
        ]),

        "params": {
            "model__criterion": ["gini", "entropy"],
            "model__max_depth": [3, 5, 8, None],
            "model__min_samples_leaf": [5, 10, 20],
            "model__class_weight": [None, "balanced"]
        }
    },

    "Random Forest": {

        "pipeline": Pipeline([
            ("model", RandomForestClassifier(
                n_estimators=300,
                random_state=42,
                n_jobs=-1
            ))
        ]),

        "params": {
            "model__max_depth": [5, 8, 12, None],
            "model__min_samples_leaf": [2, 5, 10],
            "model__max_features": ["sqrt", None],
            "model__class_weight": [None, "balanced"]
        }
    }
}

# --------------------------------------------------
# 5. Tune and evaluate each model
# --------------------------------------------------

results = []
best_parameters = {}

for model_name, config in models.items():

    print("\n" + "=" * 60)
    print("Training:", model_name)
    print("=" * 60)

    search = GridSearchCV(
        estimator=config["pipeline"],
        param_grid=config["params"],
        scoring="average_precision",
        cv=cv,
        n_jobs=-1,
        refit=True,
        verbose=1
    )

    # Hyperparameter tuning uses training data only
    search.fit(X_train, y_train)

    best_model = search.best_estimator_

    # Evaluate once on the untouched chronological test set
    predictions = best_model.predict(X_test)
    probabilities = best_model.predict_proba(X_test)[:, 1]

    # Calculate evaluation metrics
    accuracy = accuracy_score(y_test, predictions)
    precision = precision_score(
        y_test, predictions, zero_division=0
    )
    recall = recall_score(
        y_test, predictions, zero_division=0
    )
    f1 = f1_score(
        y_test, predictions, zero_division=0
    )
    roc_auc = roc_auc_score(y_test, probabilities)
    pr_auc = average_precision_score(y_test, probabilities)
    balanced_acc = balanced_accuracy_score(y_test, predictions)

    cm = confusion_matrix(
        y_test, predictions, labels=[0, 1]
    )

    # Store results
    results.append({
        "Model": model_name,
        "CV_PR_AUC": search.best_score_,
        "Accuracy": accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1_Score": f1,
        "ROC_AUC": roc_auc,
        "PR_AUC": pr_auc,
        "Balanced_Accuracy": balanced_acc,
        "TN": int(cm[0, 0]),
        "FP": int(cm[0, 1]),
        "FN": int(cm[1, 0]),
        "TP": int(cm[1, 1])
    })

    best_parameters[model_name] = search.best_params_

    # Save the tuned model
    safe_name = model_name.lower().replace(" ", "_")

    joblib.dump(
        best_model,
        MODEL_DIR / f"{safe_name}.joblib"
    )

    print("\nBest CV Average Precision:", search.best_score_)
    print("Best parameters:", search.best_params_)

    print("\nTest metrics:")
    print("Accuracy:", round(accuracy, 4))
    print("Precision:", round(precision, 4))
    print("Recall:", round(recall, 4))
    print("F1-score:", round(f1, 4))
    print("ROC-AUC:", round(roc_auc, 4))
    print("PR-AUC:", round(pr_auc, 4))
    print("Balanced accuracy:", round(balanced_acc, 4))

    print("\nConfusion matrix:")
    print(cm)

    print("\nClassification report:")
    print(classification_report(
        y_test,
        predictions,
        target_names=["Not underserved", "Underserved"],
        zero_division=0
    ))

# --------------------------------------------------
# 6. Save comparison results
# --------------------------------------------------

results_df = pd.DataFrame(results)

results_df = results_df.sort_values(
    by="PR_AUC",
    ascending=False
)

results_path = RESULT_DIR / "national_model_comparison.csv"

results_df.to_csv(results_path, index=False)

# Save best hyperparameters
params_path = RESULT_DIR / "national_best_parameters.json"

with open(params_path, "w") as file:
    json.dump(best_parameters, file, indent=4)

print("\n" + "=" * 60)
print("FINAL MODEL COMPARISON")
print("=" * 60)

print(results_df.to_string(index=False))

print("\nSaved comparison:", results_path)
print("Saved parameters:", params_path)
print("Saved models:", MODEL_DIR)
