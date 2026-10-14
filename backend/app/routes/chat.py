"""RAG chat API route."""

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import ChatRequest, ChatResponse
from app.services.rag_service import chat_with_data


router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
def ask_about_customer_data(request: ChatRequest) -> ChatResponse:
    """Answer a question using the indexed churn dataset."""
    try:
        return chat_with_data(request.question)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error