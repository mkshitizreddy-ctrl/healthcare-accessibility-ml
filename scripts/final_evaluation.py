
# Final Evaluation and Visualisation
# National Healthcare Accessibility Assessment Project

from pathlib import Path
import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
    roc_curve,
    precision_recall_curve,
    ConfusionMatrixDisplay
)

# --------------------------------------------------
# 1. Project paths
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = ROOT / "processed" / "national_temporal_ml_dataset.csv"
DHAI_PATH = ROOT / "processed" / "national_dhai_results.csv"

MODEL_DIR = ROOT / "models"
RESULT_DIR = ROOT / "results"

RESULT_DIR.mkdir(exist_ok=True)

# --------------------------------------------------
# 2. Load chronological test dataset
# --------------------------------------------------

data = pd.read_csv(DATA_PATH)

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

X_test = test[features]
y_test = test["underserved_tp1"].astype(int)

# --------------------------------------------------
# 3. Load trained models
# --------------------------------------------------

model_files = {
    "Logistic Regression": "logistic_regression.joblib",
    "Decision Tree": "decision_tree.joblib",
    "Random Forest": "random_forest.joblib"
}

models = {}

for name, filename in model_files.items():
    models[name] = joblib.load(MODEL_DIR / filename)

# --------------------------------------------------
# 4. Calculate model metrics
# --------------------------------------------------

results = []
predictions_dict = {}
probabilities_dict = {}

for name, pipeline in models.items():

    predictions = pipeline.predict(X_test)
    probabilities = pipeline.predict_proba(X_test)[:, 1]

    predictions_dict[name] = predictions
    probabilities_dict[name] = probabilities

    cm = confusion_matrix(
        y_test,
        predictions,
        labels=[0, 1]
    )

    results.append({
        "Model": name,
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
        "PR_AUC": average_precision_score(
            y_test, probabilities
        ),
        "TN": cm[0, 0],
        "FP": cm[0, 1],
        "FN": cm[1, 0],
        "TP": cm[1, 1]
    })

# --------------------------------------------------
# 5. Persistence baseline
# --------------------------------------------------

dhai = pd.read_csv(DHAI_PATH)

previous_labels = dhai[
    ["unit_id", "year", "underserved"]
].rename(columns={
    "year": "year_t",
    "underserved": "underserved_t"
})

test = test.merge(
    previous_labels,
    on=["unit_id", "year_t"],
    how="left",
    validate="one_to_one"
)

if test["underserved_t"].isna().any():
    raise ValueError("Missing previous-year labels.")

persistence_predictions = test["underserved_t"].astype(int).values

# Binary previous-year status is used as a ranking score
persistence_scores = persistence_predictions.astype(float)

predictions_dict["Persistence Baseline"] = persistence_predictions
probabilities_dict["Persistence Baseline"] = persistence_scores

cm = confusion_matrix(
    y_test,
    persistence_predictions,
    labels=[0, 1]
)

results.append({
    "Model": "Persistence Baseline",
    "Accuracy": accuracy_score(y_test, persistence_predictions),
    "Precision": precision_score(
        y_test, persistence_predictions, zero_division=0
    ),
    "Recall": recall_score(
        y_test, persistence_predictions, zero_division=0
    ),
    "F1_Score": f1_score(
        y_test, persistence_predictions, zero_division=0
    ),
    "ROC_AUC": roc_auc_score(y_test, persistence_scores),
    "PR_AUC": average_precision_score(
        y_test, persistence_scores
    ),
    "TN": cm[0, 0],
    "FP": cm[0, 1],
    "FN": cm[1, 0],
    "TP": cm[1, 1]
})

# --------------------------------------------------
# 6. Save consolidated metrics
# --------------------------------------------------

results_df = pd.DataFrame(results)

results_df = results_df.sort_values(
    by="PR_AUC",
    ascending=False
)

results_df.to_csv(
    RESULT_DIR / "final_model_comparison.csv",
    index=False
)

print("\n--- FINAL MODEL COMPARISON ---")
print(results_df.to_string(index=False))

# --------------------------------------------------
# 7. ROC curve
# --------------------------------------------------

plt.figure(figsize=(9, 7))

for name, scores in probabilities_dict.items():

    fpr, tpr, _ = roc_curve(y_test, scores)

    auc = roc_auc_score(y_test, scores)

    plt.plot(
        fpr,
        tpr,
        label=f"{name} (AUC={auc:.3f})"
    )

plt.plot(
    [0, 1],
    [0, 1],
    linestyle="--",
    label="Random classifier"
)

plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("ROC Curve Comparison")
plt.legend()
plt.grid(alpha=0.3)

plt.savefig(
    RESULT_DIR / "final_roc_curve.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()

# --------------------------------------------------
# 8. Precision-Recall curve
# --------------------------------------------------

plt.figure(figsize=(9, 7))

for name, scores in probabilities_dict.items():

    precision, recall, _ = precision_recall_curve(
        y_test,
        scores
    )

    ap = average_precision_score(y_test, scores)

    plt.plot(
        recall,
        precision,
        label=f"{name} (AP={ap:.3f})"
    )

plt.xlabel("Recall")
plt.ylabel("Precision")
plt.title("Precision-Recall Curve Comparison")
plt.legend()
plt.grid(alpha=0.3)

plt.savefig(
    RESULT_DIR / "final_precision_recall_curve.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()

# --------------------------------------------------
# 9. Confusion matrices
# --------------------------------------------------

for name, predictions in predictions_dict.items():

    cm = confusion_matrix(
        y_test,
        predictions,
        labels=[0, 1]
    )

    fig, ax = plt.subplots(figsize=(6, 5))

    display = ConfusionMatrixDisplay(
        confusion_matrix=cm,
        display_labels=[
            "Not underserved",
            "Underserved"
        ]
    )

    display.plot(
        ax=ax,
        cmap="Blues",
        values_format="d"
    )

    ax.set_title(f"Confusion Matrix - {name}")

    plt.tight_layout()

    filename = name.lower().replace(" ", "_")

    plt.savefig(
        RESULT_DIR / f"confusion_matrix_{filename}.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

# --------------------------------------------------
# 10. SHAP feature importance graph
# --------------------------------------------------

shap_path = RESULT_DIR / "shap_feature_importance.csv"

if shap_path.exists():

    shap_data = pd.read_csv(shap_path)

    shap_data = shap_data.sort_values(
        "Mean_Absolute_SHAP",
        ascending=True
    )

    plt.figure(figsize=(9, 6))

    plt.barh(
        shap_data["Feature"],
        shap_data["Mean_Absolute_SHAP"]
    )

    plt.xlabel("Mean Absolute SHAP Value")
    plt.title("Random Forest SHAP Feature Importance")
    plt.grid(axis="x", alpha=0.3)

    plt.tight_layout()

    plt.savefig(
        RESULT_DIR / "final_shap_importance.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

# --------------------------------------------------
# 11. Threshold sensitivity graph
# --------------------------------------------------

threshold_path = RESULT_DIR / "threshold_sensitivity_results.csv"

if threshold_path.exists():

    threshold_data = pd.read_csv(threshold_path)

    plt.figure(figsize=(9, 6))

    for metric in ["Accuracy", "Precision", "Recall", "F1_Score"]:

        plt.plot(
            threshold_data["Percentile"],
            threshold_data[metric],
            marker="o",
            label=metric
        )

    plt.xlabel("D-HAI Threshold Percentile")
    plt.ylabel("Score")
    plt.title("Threshold Sensitivity Analysis")
    plt.xticks([20, 25, 30])
    plt.legend()
    plt.grid(alpha=0.3)

    plt.savefig(
        RESULT_DIR / "final_threshold_sensitivity.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

# --------------------------------------------------
# 12. Anomaly sensitivity graph
# --------------------------------------------------

anomaly_path = RESULT_DIR / "anomaly_sensitivity_results.csv"

if anomaly_path.exists():

    anomaly_data = pd.read_csv(anomaly_path)

    plt.figure(figsize=(9, 6))

    metrics = ["Accuracy", "Precision", "Recall", "F1_Score"]

    x = np.arange(len(metrics))
    width = 0.35

    for index, row in anomaly_data.iterrows():

        values = [row[metric] for metric in metrics]

        plt.bar(
            x + (index - 0.5) * width,
            values,
            width,
            label=row["Scenario"]
        )

    plt.xticks(x, metrics)
    plt.ylabel("Score")
    plt.title("Anomaly Handling Sensitivity")
    plt.legend()
    plt.grid(axis="y", alpha=0.3)

    plt.tight_layout()

    plt.savefig(
        RESULT_DIR / "final_anomaly_sensitivity.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

# --------------------------------------------------
# 13. Save final test predictions
# --------------------------------------------------

prediction_output = test[
    [
        "unit_id",
        "state",
        "unit_name",
        "year_t",
        "year_tp1",
        "underserved_tp1"
    ]
].copy()

for name, predictions in predictions_dict.items():

    column = name.lower().replace(" ", "_")

    prediction_output[column + "_prediction"] = predictions

    prediction_output[column + "_score"] = (
        probabilities_dict[name]
    )

prediction_output.to_csv(
    RESULT_DIR / "final_test_predictions.csv",
    index=False
)

# --------------------------------------------------
# 14. Final output
# --------------------------------------------------

print("\n" + "=" * 60)
print("FINAL EVALUATION COMPLETED")
print("=" * 60)

print("\nGenerated files inside results/:")
for path in sorted(RESULT_DIR.glob("final_*")):
    print(path.name)

print("\nAll final evaluation files saved successfully!")
