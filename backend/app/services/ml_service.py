"""Load the trained churn pipeline and perform validated predictions."""

from functools import lru_cache

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.pipeline import Pipeline

from app.config import get_settings
from app.models.schemas import (
    CustomerFeatures,
    FeatureContribution,
    PredictionResponse,
)
from app.utils.data_loader import CATEGORICAL_FEATURES, FEATURE_COLUMNS


@lru_cache(maxsize=1)
def _load_model() -> Pipeline:
    """Load the serialized sklearn pipeline once per process."""
    model_path = get_settings().model_path
    if not model_path.is_file():
        raise FileNotFoundError(
            f"Trained model not found at {model_path}. "
            "Run `python scripts/train_model.py` from the backend directory first."
        )

    model = joblib.load(model_path)
    if not isinstance(model, Pipeline):
        raise TypeError(
            f"Expected a scikit-learn Pipeline at {model_path}, "
            f"got {type(model).__name__}."
        )
    if list(getattr(model, "feature_names_in_", ())) != FEATURE_COLUMNS:
        raise ValueError(
            "The trained model does not use the current 19-feature profile. "
            "Run `python scripts/train_model.py` from the backend directory to retrain it."
        )
    return model


@lru_cache(maxsize=1)
def _load_shap_explainer() -> shap.TreeExplainer:
    """Build the class probability explainer once per loaded model."""
    model = _load_model()
    return shap.TreeExplainer(model.named_steps["classifier"])


def predict_churn(features: CustomerFeatures) -> PredictionResponse:
    """Predict churn and return SHAP contributions grouped by input feature."""
    model = _load_model()
    feature_values = {name: getattr(features, name) for name in FEATURE_COLUMNS}
    for name in CATEGORICAL_FEATURES:
        if feature_values[name] is None:
            feature_values[name] = "Unknown"
    input_data = pd.DataFrame([feature_values], columns=FEATURE_COLUMNS)

    preprocessor = model.named_steps["preprocessor"]
    classifier = model.named_steps["classifier"]
    transformed = preprocessor.transform(input_data)
    probabilities = classifier.predict_proba(transformed)[0]
    class_labels = list(model.classes_)
    try:
        churn_class_index = class_labels.index(1)
    except ValueError as error:
        raise ValueError("The trained model does not contain churn class 1.") from error
    churn_probability = float(probabilities[churn_class_index])
    churn_prediction = bool(classifier.predict(transformed)[0])

    explainer = _load_shap_explainer()
    raw_shap_values = np.asarray(explainer.shap_values(transformed))
    if raw_shap_values.ndim == 3:
        feature_shap_values = raw_shap_values[0, :, churn_class_index]
    elif raw_shap_values.ndim == 2:
        feature_shap_values = raw_shap_values[0]
    else:
        raise ValueError(
            f"Unexpected SHAP value shape: {raw_shap_values.shape!r}."
        )

    expected_values = np.asarray(explainer.expected_value).reshape(-1)
    if expected_values.size > 1:
        baseline_probability = float(expected_values[churn_class_index])
    else:
        baseline_probability = float(expected_values[0])

    transformed_feature_names = preprocessor.get_feature_names_out()
    grouped_impacts: dict[str, float] = {}
    feature_display_names = {
        "tenure": "Tenure",
        "monthly_charges": "Monthly charges",
        "total_charges": "Total charges",
        "senior_citizen": "Senior citizen",
        "gender": "Gender",
        "partner": "Partner",
        "dependents": "Dependents",
        "phone_service": "Phone service",
        "multiple_lines": "Multiple lines",
        "internet_service": "Internet service",
        "online_security": "Online security",
        "online_backup": "Online backup",
        "device_protection": "Device protection",
        "tech_support": "Tech support",
        "streaming_tv": "Streaming TV",
        "streaming_movies": "Streaming movies",
        "contract_type": "Contract type",
        "paperless_billing": "Paperless billing",
        "payment_method": "Payment method",
    }
    for encoded_name, contribution in zip(
        transformed_feature_names, feature_shap_values, strict=True
    ):
        original_name = str(encoded_name).split("__", maxsplit=1)[-1]
        feature_name = next(
            (
                name
                for name in FEATURE_COLUMNS
                if original_name == name or original_name.startswith(f"{name}_")
            ),
            original_name,
        )
        grouped_impacts[feature_name] = (
            grouped_impacts.get(feature_name, 0.0) + float(contribution)
        )

    input_values = {}
    for name in FEATURE_COLUMNS:
        value = feature_values[name]
        if value is None:
            input_values[name] = "Unknown"
        elif name == "tenure":
            input_values[name] = f"{value} months"
        elif name == "monthly_charges":
            input_values[name] = f"${float(value):.2f}/month"
        elif name == "total_charges":
            input_values[name] = f"${float(value):.2f}"
        elif name == "senior_citizen":
            input_values[name] = "Yes" if value else "No"
        else:
            input_values[name] = str(value)
    explanations = [
        FeatureContribution(
            feature=feature_display_names[name],
            value=input_values[name],
            impact=impact,
        )
        for name, impact in grouped_impacts.items()
    ]
    explanations.sort(key=lambda item: abs(item.impact), reverse=True)

    if churn_prediction:
        message = "This customer is predicted to churn."
    else:
        message = "This customer is predicted to stay."

    return PredictionResponse(
        churn_prediction=churn_prediction,
        churn_probability=churn_probability,
        message=message,
        baseline_probability=baseline_probability,
        explanations=explanations,
    )