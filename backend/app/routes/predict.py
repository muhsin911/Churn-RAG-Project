"""Churn prediction API route."""

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import CustomerFeatures, PredictionResponse
from app.services.ml_service import predict_churn


router = APIRouter(tags=["predictions"])


@router.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
)
def predict_customer_churn(customer: CustomerFeatures) -> PredictionResponse:
    """Predict churn for one customer."""
    try:
        return predict_churn(customer)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not calculate churn prediction: {error}",
        ) from error