"""Initialize PostgreSQL with real historical rows and unlabeled synthetic profiles."""

from collections.abc import Iterable

import numpy as np
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.customer import CustomerRecord
from app.utils.data_loader import load_telco_data


TARGET_CUSTOMERS = 30_000
SYNTHETIC_ID_PREFIX = "SYN"

CONTEXT_FIELDS = [
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


def _real_customer_rows(dataset: pd.DataFrame) -> Iterable[dict[str, object]]:
    for row in dataset.to_dict(orient="records"):
        record: dict[str, object] = {
            "customer_id": str(row["customer_id"]),
            "tenure": int(row["tenure"]),
            "monthly_charges": float(row["monthly_charges"]),
            "total_charges": float(row["total_charges"]),
            "contract_type": str(row["contract_type"]),
            "payment_method": str(row["payment_method"]),
            "actual_churn": bool(row["churn_label"]),
            "predicted_churn": None,
            "churn_probability": None,
            "record_source": "telco_original",
        }
        record.update(
            {
                field: int(row[field]) if field == "senior_citizen" else str(row[field])
                for field in CONTEXT_FIELDS
            }
        )
        yield record


def _synthetic_customer_rows(
    dataset: pd.DataFrame,
    count: int,
    existing_count: int,
) -> Iterable[dict[str, object]]:
    rng = np.random.default_rng(20261013)
    samples = dataset.iloc[rng.integers(0, len(dataset), size=count)]
    for offset, (_, row) in enumerate(samples.iterrows(), start=1):
        tenure = int(np.clip(int(row["tenure"]) + rng.integers(-3, 4), 0, 120))
        monthly = round(
            float(np.clip(float(row["monthly_charges"]) + rng.normal(0, 2.5), 18, 120)),
            2,
        )
        record: dict[str, object] = {
            "customer_id": f"{SYNTHETIC_ID_PREFIX}-{existing_count + offset:08d}",
            "tenure": tenure,
            "monthly_charges": monthly,
            "total_charges": round(tenure * monthly, 2),
            "contract_type": str(row["contract_type"]),
            "payment_method": str(row["payment_method"]),
            "actual_churn": None,
            "predicted_churn": None,
            "churn_probability": None,
            "record_source": "synthetic",
        }
        record.update(
            {
                field: int(row[field]) if field == "senior_citizen" else str(row[field])
                for field in CONTEXT_FIELDS
            }
        )
        yield record


def seed_customer_records(session: Session) -> int:
    """Ensure at least 30,000 uniquely identified records exist without fake labels."""
    current_count = session.scalar(select(func.count()).select_from(CustomerRecord)) or 0
    if current_count >= TARGET_CUSTOMERS:
        return int(current_count)

    dataset = load_telco_data()
    rows: list[dict[str, object]] = []
    if current_count == 0:
        rows.extend(_real_customer_rows(dataset))

    count_after_real = current_count + len(rows)
    synthetic_count = max(0, TARGET_CUSTOMERS - count_after_real)
    rows.extend(
        _synthetic_customer_rows(dataset, synthetic_count, current_count)
    )
    if rows:
        for start in range(0, len(rows), 1_000):
            statement = insert(CustomerRecord).values(
                rows[start : start + 1_000]
            ).on_conflict_do_nothing(
                index_elements=[CustomerRecord.customer_id]
            )
            session.execute(statement)
        session.commit()
    return int(
        session.scalar(select(func.count()).select_from(CustomerRecord)) or 0
    )
