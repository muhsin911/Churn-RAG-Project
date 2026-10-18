"""Train and evaluate a Random Forest churn classification pipeline."""

import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.data_loader import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    load_telco_data,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT_DIR / "data" / "processed" / "model.pkl"
TARGET_COLUMN = "churn_label"
def train_pipeline(
    dataset: pd.DataFrame,
) -> tuple[Pipeline, dict[str, float]]:
    """Fit the pipeline and return metrics measured on a held-out split."""
    required_columns = set(FEATURE_COLUMNS + [TARGET_COLUMN])
    missing_columns = sorted(required_columns.difference(dataset.columns))
    if missing_columns:
        raise ValueError(
            "Dataset is missing required columns: " + ", ".join(missing_columns)
        )
    if dataset.empty:
        raise ValueError("The Telco churn dataset contains no customer rows.")

    features = dataset[FEATURE_COLUMNS]
    target = dataset[TARGET_COLUMN]
    if target.nunique() < 2:
        raise ValueError(
            f"{TARGET_COLUMN} must contain both churn classes to train a classifier."
        )

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=0.20,
        random_state=42,
        stratify=target,
    )

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
            (
                "numeric",
                Pipeline([("imputer", SimpleImputer(strategy="most_frequent"))]),
                NUMERIC_FEATURES,
            ),
        ],
        remainder="drop",
    )
    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=300,
                    random_state=42,
                    class_weight="balanced_subsample",
                    n_jobs=-1,
                ),
            ),
        ]
    )

    model.fit(x_train, y_train)
    predictions = model.predict(x_test)

    metrics = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "f1_score": float(f1_score(y_test, predictions, zero_division=0)),
    }
    return model, metrics


def main() -> None:
    """Train, evaluate, and save a model from the original Telco dataset."""
    dataset = load_telco_data()
    model, metrics = train_pipeline(dataset)

    print("Test-set metrics (20% holdout):")
    print(f"  Source rows: {len(dataset):,}")
    print(f"  Churn rate:  {dataset[TARGET_COLUMN].mean():.1%}")
    for metric_name, value in metrics.items():
        print(f"  {metric_name.replace('_', ' ').title()}: {value:.3f}")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"Saved trained model pipeline to: {MODEL_PATH}")


if __name__ == "__main__":
    main()