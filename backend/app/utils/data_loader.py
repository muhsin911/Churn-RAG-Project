"""Load and normalize the original Telco churn CSV for ML and RAG."""

from pathlib import Path

import numpy as np
import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parents[2]
TELCO_CSV_PATH = (
    BACKEND_DIR / "data" / "raw" / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
)
NORMALIZED_COLUMNS = [
    "customer_id",
    "tenure",
    "monthly_charges",
    "total_charges",
    "contract_type",
    "payment_method",
    "churn_label",
]
CUSTOMER_CONTEXT_COLUMNS = [
    "gender",
    "senior_citizen",
    "partner",
    "dependents",
    "phone_service",
    "multiple_lines",
    "internet_service",
    "online_security",
    "online_backup",
    "device_protection",
    "tech_support",
    "streaming_tv",
    "streaming_movies",
    "paperless_billing",
]
SOURCE_COLUMNS = {
    "customerID",
    "gender",
    "SeniorCitizen",
    "Partner",
    "Dependents",
    "tenure",
    "PhoneService",
    "MultipleLines",
    "InternetService",
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
    "Contract",
    "PaperlessBilling",
    "PaymentMethod",
    "MonthlyCharges",
    "TotalCharges",
    "Churn",
}
ALLOWED_CATEGORIES = {
    "gender": {"Female", "Male"},
    "Partner": {"Yes", "No"},
    "Dependents": {"Yes", "No"},
    "PhoneService": {"Yes", "No"},
    "MultipleLines": {"Yes", "No", "No phone service"},
    "InternetService": {"DSL", "Fiber optic", "No"},
    "OnlineSecurity": {"Yes", "No", "No internet service"},
    "OnlineBackup": {"Yes", "No", "No internet service"},
    "DeviceProtection": {"Yes", "No", "No internet service"},
    "TechSupport": {"Yes", "No", "No internet service"},
    "StreamingTV": {"Yes", "No", "No internet service"},
    "StreamingMovies": {"Yes", "No", "No internet service"},
    "Contract": {"Month-to-month", "One year", "Two year"},
    "PaperlessBilling": {"Yes", "No"},
    "PaymentMethod": {
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)",
    },
}


def load_telco_data(csv_path: Path | None = None) -> pd.DataFrame:
    """Load the source CSV and return cleaned columns shared by ML and RAG.

    Empty TotalCharges values in this dataset correspond to customers with
    zero tenure. Those values are filled with zero; other missing charges fail
    validation rather than being silently imputed.
    """
    if csv_path is None:
        csv_path = TELCO_CSV_PATH
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Original Telco churn CSV not found at {csv_path}. "
            "Place WA_Fn-UseC_-Telco-Customer-Churn.csv in backend/data/raw/."
        )

    source = pd.read_csv(csv_path, na_values=[" "])
    missing_columns = sorted(SOURCE_COLUMNS.difference(source.columns))
    if missing_columns:
        raise ValueError(
            "Telco CSV is missing required columns: " + ", ".join(missing_columns)
        )
    if source.empty:
        raise ValueError(f"Telco CSV is empty: {csv_path}")

    tenure = pd.to_numeric(source["tenure"], errors="raise")
    total_charges = pd.to_numeric(source["TotalCharges"], errors="coerce")
    monthly_charges = pd.to_numeric(source["MonthlyCharges"], errors="raise")
    senior_citizen = pd.to_numeric(source["SeniorCitizen"], errors="raise")
    missing_charges = total_charges.isna()
    if missing_charges.any():
        zero_tenure_missing = missing_charges & tenure.eq(0)
        unexpected_missing = missing_charges & ~tenure.eq(0)
        if unexpected_missing.any():
            customer_ids = source.loc[unexpected_missing, "customerID"].astype(str)
            raise ValueError(
                "TotalCharges is missing for customers with non-zero tenure: "
                + ", ".join(customer_ids.head(10))
            )
        total_charges = total_charges.mask(zero_tenure_missing, 0.0)

    for column, values in {
        "tenure": tenure,
        "MonthlyCharges": monthly_charges,
        "TotalCharges": total_charges,
    }.items():
        if not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError(f"{column} contains a non-finite numeric value.")

    for column, allowed_values in ALLOWED_CATEGORIES.items():
        values = source[column].astype("string").str.strip()
        invalid_values = sorted(set(values.dropna().unique()) - allowed_values)
        if values.isna().any() or invalid_values:
            raise ValueError(
                f"Unexpected values in {column}: "
                f"{invalid_values or ['blank value']}"
            )

    customer_ids = source["customerID"].astype("string").str.strip()
    if customer_ids.isna().any() or customer_ids.str.len().eq(0).any():
        raise ValueError("Telco CSV contains an empty customerID value.")
    if customer_ids.duplicated().any():
        raise ValueError("Telco CSV contains duplicate customerID values.")
    if tenure.lt(0).any() or tenure.gt(120).any():
        raise ValueError("Tenure values must be between 0 and 120 months.")
    if not senior_citizen.isin([0, 1]).all():
        raise ValueError("SeniorCitizen values must be 0 or 1.")
    if monthly_charges.lt(0).any() or total_charges.lt(0).any():
        raise ValueError("MonthlyCharges and TotalCharges cannot be negative.")

    churn_values = source["Churn"].astype("string").str.strip().str.lower()
    invalid_churn = ~churn_values.isin(["yes", "no"])
    if invalid_churn.any():
        values = sorted(churn_values[invalid_churn].dropna().unique().tolist())
        raise ValueError(f"Unexpected Churn values: {values}")

    payment_method = (
        source["PaymentMethod"]
        .astype("string")
        .str.replace(" (automatic)", "", regex=False)
        .str.strip()
    )
    normalized = pd.DataFrame(
        {
            "customer_id": customer_ids,
            "tenure": tenure.astype(int),
            "monthly_charges": monthly_charges.astype(float),
            "total_charges": total_charges.astype(float),
            "contract_type": source["Contract"].astype("string").str.strip(),
            "payment_method": payment_method,
            "churn_label": churn_values.map({"no": 0, "yes": 1}).astype(int),
            "gender": source["gender"].astype("string").str.strip(),
            "senior_citizen": senior_citizen.astype(int),
            "partner": source["Partner"].astype("string").str.strip(),
            "dependents": source["Dependents"].astype("string").str.strip(),
            "phone_service": source["PhoneService"].astype("string").str.strip(),
            "multiple_lines": source["MultipleLines"].astype("string").str.strip(),
            "internet_service": source["InternetService"].astype("string").str.strip(),
            "online_security": source["OnlineSecurity"].astype("string").str.strip(),
            "online_backup": source["OnlineBackup"].astype("string").str.strip(),
            "device_protection": source["DeviceProtection"].astype("string").str.strip(),
            "tech_support": source["TechSupport"].astype("string").str.strip(),
            "streaming_tv": source["StreamingTV"].astype("string").str.strip(),
            "streaming_movies": source["StreamingMovies"].astype("string").str.strip(),
            "paperless_billing": source["PaperlessBilling"].astype("string").str.strip(),
        }
    )

    all_columns = NORMALIZED_COLUMNS + CUSTOMER_CONTEXT_COLUMNS
    if normalized[all_columns].isna().any().any():
        missing = normalized[all_columns].columns[
            normalized[all_columns].isna().any()
        ].tolist()
        raise ValueError(
            "Unexpected missing values remain after cleaning: " + ", ".join(missing)
        )
    return normalized[all_columns]