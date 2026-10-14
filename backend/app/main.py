"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.models.customer import CustomerRecord
from app.routes import chat, customers, dataset, predict
from app.services.customer_seed_service import seed_customer_records
from app.services.rag_index_service import start_database_index_sync


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Create the customer table and seed it once before serving requests."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed_customer_records(session)
    start_database_index_sync()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Customer CRUD, churn predictions, and retrieval-augmented Q&A.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(predict.router)
app.include_router(chat.router)
app.include_router(dataset.router)
app.include_router(customers.router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Report that the API process is running."""
    return {"status": "ok"}