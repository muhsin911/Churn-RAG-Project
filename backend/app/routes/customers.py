"""Paginated customer CRUD and prediction-by-ID API."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.customer import CustomerRecord
from app.models.schemas import (
    CustomerCreate,
    CustomerPage,
    CustomerPatch,
    CustomerResponse,
    PredictionResponse,
)
from app.services.customer_service import (
    create_customer,
    delete_customer,
    get_customer,
    list_customers,
    patch_customer,
    predict_customer_by_id,
    replace_customer,
)
from app.services.rag_index_service import (
    RagIndexSyncError,
    delete_customer_document,
    sync_customer_record,
)


router = APIRouter(prefix="/customers", tags=["customers"])


def _sync_saved_customer(record: CustomerRecord) -> None:
    """Make a committed customer change available to semantic search."""
    try:
        sync_customer_record(record)
    except RagIndexSyncError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"Customer {record.customer_id} was saved to PostgreSQL, "
                "but its RAG search document could not be updated. "
                "Check the backend logs and retry the update."
            ),
        ) from error


@router.get("", response_model=CustomerPage)
def get_customers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    search: str | None = Query(default=None, max_length=64),
    session: Session = Depends(get_db),
) -> CustomerPage:
    """Return a page of customers, optionally searching by customer ID."""
    return list_customers(session, page, page_size, search)


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_customer(
    data: CustomerCreate,
    session: Session = Depends(get_db),
) -> CustomerResponse:
    """Create one manually entered customer."""
    try:
        record = create_customer(session, data)
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That customer ID already exists.",
        ) from error
    _sync_saved_customer(record)
    return CustomerResponse.model_validate(record)


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer_by_id(
    customer_id: str,
    session: Session = Depends(get_db),
) -> CustomerResponse:
    """Retrieve one customer by unique ID."""
    record = get_customer(session, customer_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} was not found.",
        )
    return CustomerResponse.model_validate(record)


@router.put("/{customer_id}", response_model=CustomerResponse)
def put_customer(
    customer_id: str,
    data: CustomerCreate,
    session: Session = Depends(get_db),
) -> CustomerResponse:
    """Replace a customer's feature and context fields."""
    try:
        record = replace_customer(session, customer_id, data)
    except ValueError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    if record is None:
        raise HTTPException(status_code=404, detail="Customer not found.")
    _sync_saved_customer(record)
    return CustomerResponse.model_validate(record)


@router.patch("/{customer_id}", response_model=CustomerResponse)
def patch_customer_by_id(
    customer_id: str,
    data: CustomerPatch,
    session: Session = Depends(get_db),
) -> CustomerResponse:
    """Update selected customer fields, including manually observed churn."""
    try:
        record = patch_customer(session, customer_id, data)
    except ValueError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    if record is None:
        raise HTTPException(status_code=404, detail="Customer not found.")
    _sync_saved_customer(record)
    return CustomerResponse.model_validate(record)


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_customer(
    customer_id: str,
    session: Session = Depends(get_db),
) -> Response:
    """Delete one customer by unique ID."""
    if not delete_customer(session, customer_id):
        raise HTTPException(status_code=404, detail="Customer not found.")
    try:
        delete_customer_document(customer_id)
    except RagIndexSyncError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"Customer {customer_id} was deleted from PostgreSQL, "
                "but its RAG search document could not be removed. "
                "Check the backend logs and retry after restoring ChromaDB."
            ),
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{customer_id}/predict", response_model=PredictionResponse)
def predict_saved_customer(
    customer_id: str,
    session: Session = Depends(get_db),
) -> PredictionResponse:
    """Predict and store the latest probability for a database customer."""
    try:
        result = predict_customer_by_id(session, customer_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="Customer not found.")
    return result[1]
