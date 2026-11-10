
from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "autointel.db"
OUT = ROOT / "outputs" / "forecasting"
OUT.mkdir(parents=True, exist_ok=True)

# Read Phase 3 cleaned data
with sqlite3.connect(DB) as conn:
    df = pd.read_sql_query(
        "SELECT * FROM forecast_monthly", conn
    )

# Prepare monthly dates
df["Date"] = pd.to_datetime(df["Date"])
df["Year"] = df["Date"].dt.year
df["Month_Num"] = df["Date"].dt.month

df = df.sort_values(
    ["Manufacturer", "Model_Name", "Date"]
).reset_index(drop=True)

# Check model-month uniqueness
keys = ["Manufacturer", "Model_Name", "Date"]
if df.duplicated(keys).any():
    raise ValueError("Duplicate model-month records found")

# Create lag features using prior records
group_cols = ["Manufacturer", "Model_Name"]
grouped = df.groupby(group_cols)["Estimated_Registrations"]

df["Lag_1"] = grouped.shift(1)
df["Lag_12"] = grouped.shift(12)

# Ensure lag values refer to the correct calendar months
previous_date = df.groupby(group_cols)["Date"].shift(1)
year_ago_date = df.groupby(group_cols)["Date"].shift(12)

df.loc[
    previous_date != df["Date"] - pd.DateOffset(months=1),
    "Lag_1"
] = np.nan

df.loc[
    year_ago_date != df["Date"] - pd.DateOffset(months=12),
    "Lag_12"
] = np.nan

df = df.dropna(subset=["Lag_1", "Lag_12"]).copy()

# Chronological train/test split
train = df[df["Year"] <= 2025]
test = df[df["Year"] == 2026]

if train.empty or test.empty:
    raise ValueError("Training or testing data is empty")

features = [
    "Year", "Month_Num", "Manufacturer",
    "Model_Name", "Lag_1", "Lag_12"
]

X_train = train[features]
X_test = test[features]
y_train = train["Estimated_Registrations"]
y_test = test["Estimated_Registrations"]

def build_model(estimator):
    preprocess = ColumnTransformer([
        (
            "category",
            OneHotEncoder(handle_unknown="ignore"),
            ["Manufacturer", "Model_Name"],
        ),
        (
            "numeric",
            "passthrough",
            ["Year", "Month_Num", "Lag_1", "Lag_12"],
        ),
    ])

    return Pipeline([
        ("preprocess", preprocess),
        ("regressor", estimator),
    ])

models = {
    "Linear Regression": build_model(
        LinearRegression()
    ),
    "Random Forest": build_model(
        RandomForestRegressor(
            n_estimators=100,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )
    ),
}

predictions = {
    "Previous Month Baseline": test["Lag_1"].to_numpy()
}

for name, model in models.items():
    print(f"Training {name}...")
    model.fit(X_train, y_train)
    predictions[name] = model.predict(X_test)

results = []
output = test[
    ["Date", "Manufacturer", "Model_Name",
     "Estimated_Registrations"]
].copy()

for name, predicted in predictions.items():
    predicted = np.maximum(np.asarray(predicted), 0)

    results.append({
        "Model": name,
        "MAE": mean_absolute_error(y_test, predicted),
        "RMSE": np.sqrt(
            mean_squared_error(y_test, predicted)
        ),
        "R2": r2_score(y_test, predicted),
    })

    output[name] = predicted

metrics = pd.DataFrame(results).sort_values("MAE")

metrics.to_csv(
    OUT / "model_comparison.csv", index=False
)
output.to_csv(
    OUT / "test_predictions.csv", index=False
)

# Actual versus predicted monthly chart
monthly = output.groupby("Date").sum(numeric_only=True)

plt.figure(figsize=(11, 5))

plt.plot(
    monthly.index,
    monthly["Estimated_Registrations"],
    marker="o",
    label="Estimated actual",
)

for name in predictions:
    plt.plot(
        monthly.index,
        monthly[name],
        marker=".",
        label=name,
    )

plt.title("AutoIntel India — 2026 Forecast Evaluation")
plt.xlabel("Month")
plt.ylabel("Estimated Registrations")
plt.legend()
plt.tight_layout()

plt.savefig(
    OUT / "actual_vs_predicted.png",
    dpi=160,
)
plt.close()

print("\nPHASE 4 — MODEL COMPARISON")
print(metrics.to_string(index=False))
print("\nTraining rows:", len(train))
print("Testing rows:", len(test))
print("Results saved to:", OUT)
