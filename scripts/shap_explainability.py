
# National Healthcare Accessibility Project
# SHAP Explainability using the trained Random Forest model
#
# This script:
# 1. Loads the trained Random Forest pipeline.
# 2. Extracts the actual Random Forest classifier.
# 3. Calculates SHAP values.
# 4. Generates global feature importance.
# 5. Generates SHAP summary and bar plots.
# 6. Explains one individual prediction.
# 7. Saves all results inside the results folder.

from pathlib import Path
import joblib
import pandas as pd
import shap
import matplotlib.pyplot as plt
import numpy as np

# --------------------------------------------------
# 1. Project paths
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

DATA_PATH = (
    ROOT / "processed" /
    "national_temporal_ml_dataset.csv"
)

MODEL_PATH = (
    ROOT / "models" /
    "random_forest.joblib"
)

RESULT_DIR = ROOT / "results"
RESULT_DIR.mkdir(exist_ok=True)

# --------------------------------------------------
# 2. Load test dataset
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

print("Test dataset loaded successfully.")
print("Test records:", len(X_test))

# --------------------------------------------------
# 3. Load trained Random Forest pipeline
# --------------------------------------------------

pipeline = joblib.load(MODEL_PATH)

# Extract the Random Forest classifier from pipeline
model = pipeline.named_steps["model"]

print("\nRandom Forest pipeline loaded successfully.")
print("Extracted model:", type(model))

# --------------------------------------------------
# 4. Create SHAP explainer
# --------------------------------------------------

# Explain the positive class: underserved (class 1)
explainer = shap.TreeExplainer(model)

shap_values = explainer.shap_values(X_test)

# --------------------------------------------------
# 5. Handle different SHAP output formats
# --------------------------------------------------

if isinstance(shap_values, list):

    # Older SHAP versions return a list for each class
    values = shap_values[1]

elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:

    # Some versions return:
    # samples x features x classes
    values = shap_values[:, :, 1]

else:

    # Some versions return a 2D array
    values = shap_values

# --------------------------------------------------
# 6. Global SHAP feature importance
# --------------------------------------------------

importance = pd.DataFrame({
    "Feature": features,
    "Mean_Absolute_SHAP": np.abs(values).mean(axis=0)
})

importance = importance.sort_values(
    by="Mean_Absolute_SHAP",
    ascending=False
)

print("\n--- SHAP FEATURE IMPORTANCE ---")
print(importance.to_string(index=False))

# Save feature importance
importance.to_csv(
    RESULT_DIR / "shap_feature_importance.csv",
    index=False
)

# --------------------------------------------------
# 7. SHAP summary plot
# --------------------------------------------------

shap.summary_plot(
    values,
    X_test,
    show=False
)

plt.title("SHAP Summary Plot - Random Forest")

plt.tight_layout()

plt.savefig(
    RESULT_DIR / "shap_summary_plot.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()

# --------------------------------------------------
# 8. SHAP bar plot
# --------------------------------------------------

shap.summary_plot(
    values,
    X_test,
    plot_type="bar",
    show=False
)

plt.title("SHAP Feature Importance - Random Forest")

plt.tight_layout()

plt.savefig(
    RESULT_DIR / "shap_bar_plot.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()

# --------------------------------------------------
# 9. Explain one individual prediction
# --------------------------------------------------

sample_index = 0

sample = X_test.iloc[[sample_index]]

prediction = model.predict(sample)[0]

probability = model.predict_proba(sample)[0][1]

actual = test.iloc[sample_index]["underserved_tp1"]

print("\n--- INDIVIDUAL PREDICTION ---")

print("Unit:", test.iloc[sample_index]["unit_name"])

print(
    "Transition:",
    test.iloc[sample_index]["year_t"],
    "to",
    test.iloc[sample_index]["year_tp1"]
)

print("Actual status:", actual)
print("Predicted status:", prediction)

print(
    "Probability of underserved:",
    round(probability, 4)
)

# --------------------------------------------------
# 10. Individual SHAP explanation
# --------------------------------------------------

base_value = explainer.expected_value

# Select the expected value for class 1
if isinstance(base_value, (list, np.ndarray)):

    base_value = np.asarray(base_value).reshape(-1)[1]

# Create an explanation object
explanation = shap.Explanation(
    values=values[sample_index],
    base_values=base_value,
    data=X_test.iloc[sample_index].values,
    feature_names=features
)

# Generate waterfall plot
shap.plots.waterfall(
    explanation,
    show=False
)

plt.title("Individual SHAP Explanation - Random Forest")

plt.tight_layout()

plt.savefig(
    RESULT_DIR / "shap_individual_explanation.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()

# --------------------------------------------------
# 11. Save SHAP values for further analysis
# --------------------------------------------------

shap_df = pd.DataFrame(
    values,
    columns=features
)

shap_df.insert(
    0,
    "unit_name",
    test["unit_name"].values
)

shap_df.insert(
    0,
    "unit_id",
    test["unit_id"].values
)

shap_df.to_csv(
    RESULT_DIR / "national_shap_values.csv",
    index=False
)

# --------------------------------------------------
# 12. Final output
# --------------------------------------------------

print("\n" + "=" * 55)
print("SHAP ANALYSIS COMPLETED SUCCESSFULLY")
print("=" * 55)

print("\nFiles saved inside results folder:")

print("1. shap_feature_importance.csv")
print("2. shap_summary_plot.png")
print("3. shap_bar_plot.png")
print("4. shap_individual_explanation.png")
print("5. national_shap_values.csv")
