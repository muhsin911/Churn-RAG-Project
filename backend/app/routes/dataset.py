"""Database-backed churn analytics endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.schemas import DatasetSummaryResponse
from app.services.customer_service import get_customer_database_summary


router = APIRouter(tags=["dataset"])


@router.get(
    "/analytics/summary",
    response_model=DatasetSummaryResponse,
)
def dataset_summary(
    session: Session = Depends(get_db),
) -> DatasetSummaryResponse:
    """Summarize records while calculating rates only from known actual outcomes."""
    return get_customer_database_summary(session)
