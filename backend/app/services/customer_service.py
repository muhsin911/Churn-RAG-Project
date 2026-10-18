"""CRUD, persisted predictions, and customer-database analytics."""

from math import ceil
from uuid import uuid4

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.customer import CustomerRecord
from app.models.schemas import (
    CustomerCreate,
    CustomerFeatures,
    CustomerPage,
    CustomerPatch,
    CustomerResponse,
    DatasetSummaryResponse,
    PredictionResponse,
)
from app.services.analytics_service import summarize_labeled_customers
from app.services.ml_service import predict_churn
from app.utils.data_loader import FEATURE_COLUMNS


def list_customers(
    session: Session,
    page: int,
    page_size: int,
    search: str | None,
) -> CustomerPage:
    """Return one paginated customer page, optionally filtered by ID."""
    query = select(CustomerRecord)
    count_query = select(func.count()).select_from(CustomerRecord)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(CustomerRecord.customer_id.ilike(pattern))
        count_query = count_query.where(CustomerRecord.customer_id.ilike(pattern))
    total = int(session.scalar(count_query) or 0)
    records = session.scalars(
        query.order_by(CustomerRecord.customer_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return CustomerPage(
        items=[CustomerResponse.model_validate(record) for record in records],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=ceil(total / page_size) if total else 0,
    )


def get_customer(session: Session, customer_id: str) -> CustomerRecord | None:
    """Return a customer by unique ID, if present."""
    return session.get(CustomerRecord, customer_id)


def create_customer(session: Session, data: CustomerCreate) -> CustomerRecord:
    """Insert one manual record, assigning a unique ID when omitted."""
    values = data.model_dump(exclude={"customer_id"})
    record = CustomerRecord(
        customer_id=data.customer_id or f"MAN-{uuid4().hex[:12].upper()}",
        record_source="manual",
        **values,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def replace_customer(
    session: Session,
    customer_id: str,
    data: CustomerCreate,
) -> CustomerRecord | None:
    """Replace a profile while preserving its actual outcome unless supplied."""
    record = get_customer(session, customer_id)
    if record is None:
        return None
    values = data.model_dump(exclude={"customer_id", "actual_churn"})
    for field, value in values.items():
        setattr(record, field, value)
    if "actual_churn" in data.model_fields_set:
        record.actual_churn = data.actual_churn
    record.predicted_churn = None
    record.churn_probability = None
    session.commit()
    session.refresh(record)
    return record


def patch_customer(
    session: Session,
    customer_id: str,
    data: CustomerPatch,
) -> CustomerRecord | None:
    """Update supplied fields; profile changes invalidate any old prediction."""
    record = get_customer(session, customer_id)
    if record is None:
        return None
    values = data.model_dump(exclude_unset=True)
    if not values:
        raise ValueError("Provide at least one field to update.")
    if any(values.get(field) is None for field in ("tenure", "monthly_charges", "total_charges", "contract_type", "payment_method") if field in values):
        raise ValueError("Required profile fields cannot be cleared.")
    profile_fields = {
        "tenure",
        "monthly_charges",
        "total_charges",
        "contract_type",
        "payment_method",
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
    }
    for field, value in values.items():
        setattr(record, field, value)
    if profile_fields.intersection(values):
        if record.tenure > 0 and record.total_charges <= 0:
            raise ValueError("total_charges must be positive when tenure is positive.")
        record.predicted_churn = None
        record.churn_probability = None
    session.commit()
    session.refresh(record)
    return record


def delete_customer(session: Session, customer_id: str) -> bool:
    """Delete one record by unique ID."""
    record = get_customer(session, customer_id)
    if record is None:
        return False
    session.delete(record)
    session.commit()
    return True


def predict_customer_by_id(
    session: Session,
    customer_id: str,
) -> tuple[CustomerRecord, PredictionResponse] | None:
    """Run the unchanged trained model for a stored profile and save its result."""
    record = get_customer(session, customer_id)
    if record is None:
        return None
    profile = {name: getattr(record, name) for name in FEATURE_COLUMNS}
    result = predict_churn(CustomerFeatures(**profile))
    record.predicted_churn = result.churn_prediction
    record.churn_probability = result.churn_probability
    session.commit()
    session.refresh(record)
    return record, result


def get_customer_database_summary(session: Session) -> DatasetSummaryResponse:
    """Summarize real recorded churn labels, excluding unknown/synthetic outcomes."""
    total_records = int(
        session.scalar(select(func.count()).select_from(CustomerRecord)) or 0
    )
    labeled_records = session.scalars(
        select(CustomerRecord).where(CustomerRecord.actual_churn.is_not(None))
    ).all()
    known = len(labeled_records)
    data = pd.DataFrame(
        [
            {
                "contract_type": record.contract_type,
                "internet_service": record.internet_service or "Unknown",
                "payment_method": record.payment_method,
                "online_security": record.online_security or "Unknown",
                "tech_support": record.tech_support or "Unknown",
                "tenure": record.tenure,
                "churn_label": int(bool(record.actual_churn)),
            }
            for record in labeled_records
        ]
    )
    result = summarize_labeled_customers(data)
    result["total_customers"] = total_records
    result["known_actual_outcomes"] = known
    result["unlabeled_customers"] = total_records - known
    return DatasetSummaryResponse(**result)
