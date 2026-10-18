"""Create a versioned persistent Chroma index from normalized customer data."""

import logging
from collections.abc import Mapping
from pathlib import Path
from threading import Lock, Thread
from uuid import uuid4

import pandas as pd
from langchain_chroma import Chroma
from langchain_core.documents import Document
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models.customer import CustomerRecord
from app.services.embedding_service import get_embeddings


logger = logging.getLogger(__name__)
_index_lock = Lock()
_vector_store_lock = Lock()
_vector_store: Chroma | None = None
COLLECTION_PREFIX = "telco_churn_"
INDEX_BATCH_SIZE = 128
CONTEXT_COLUMNS = [
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


class RagIndexSyncError(RuntimeError):
    """A PostgreSQL customer change could not be reflected in ChromaDB."""


def get_vector_store() -> Chroma:
    """Return the active persistent Chroma collection shared by RAG operations."""
    global _vector_store
    with _vector_store_lock:
        if _vector_store is None:
            settings = get_settings()
            settings.chroma_path.mkdir(parents=True, exist_ok=True)
            _vector_store = Chroma(
                collection_name=active_collection_name(),
                embedding_function=get_embeddings(),
                persist_directory=str(settings.chroma_path),
            )
        return _vector_store


def _customer_document(row: Mapping[str, object]) -> Document:
    actual_churn = row.get("actual_churn")
    if actual_churn is None and "churn_label" in row:
        actual_churn = bool(row["churn_label"])
    actual_text = (
        "Unknown" if actual_churn is None else "Yes" if actual_churn else "No"
    )
    customer_id = str(row["customer_id"])
    tenure = int(row["tenure"])
    monthly_charges = float(row["monthly_charges"])
    total_charges = float(row["total_charges"])
    contract_type = str(row["contract_type"])
    payment_method = str(row["payment_method"])
    context_fields = [
        *CONTEXT_COLUMNS,
        "internet_service",
        "online_security",
        "tech_support",
        "paperless_billing",
    ]
    context = "; ".join(
        f"{field.replace('_', ' ')}: {row[field]}"
        for field in dict.fromkeys(context_fields)
        if row.get(field) is not None
    )
    source = str(row.get("record_source", "telco_original"))
    content = (
        f"Customer {customer_id} has tenure {tenure} months, monthly charges "
        f"${monthly_charges:.2f}, total charges ${total_charges:.2f}, contract "
        f"type {contract_type}, and payment method {payment_method}. "
        f"Actual churn outcome: {actual_text}. Record source: {source}. "
        f"Additional customer details: {context or 'not recorded'}."
    )
    metadata: dict[str, str | int | float] = {
        "customer_id": customer_id,
        "tenure": tenure,
        "monthly_charges": monthly_charges,
        "total_charges": total_charges,
        "contract_type": contract_type,
        "payment_method": payment_method,
        "actual_churn": actual_text,
        "record_source": source,
    }
    for field in CONTEXT_COLUMNS:
        value = row.get(field)
        if value is not None:
            metadata[field] = int(value) if field == "senior_citizen" else str(value)
    return Document(page_content=content, metadata=metadata)


def make_customer_documents(dataset: pd.DataFrame) -> list[Document]:
    """Format every normalized row as a searchable customer record."""
    rows = dataset.to_dict(orient="records")
    for row in rows:
        row["actual_churn"] = bool(row["churn_label"])
        row["record_source"] = "telco_original"
    return [_customer_document(row) for row in rows]


def customer_record_document(record: CustomerRecord) -> Document:
    """Build a searchable document reflecting the current PostgreSQL profile."""
    return _customer_document(
        {
            column.name: getattr(record, column.name)
            for column in CustomerRecord.__table__.columns
        }
    )


def sync_database_index(session: Session) -> int:
    """Index database profiles missing from Chroma, including synthetic examples."""
    with _index_lock:
        vector_store = get_vector_store()
        indexed_ids = set(vector_store.get(include=[])["ids"])
    customer_ids = session.scalars(
        select(CustomerRecord.customer_id)
        .order_by(CustomerRecord.customer_id)
    ).all()
    pending_ids = [
        customer_id for customer_id in customer_ids if customer_id not in indexed_ids
    ]
    indexed_count = 0
    for start in range(0, len(pending_ids), INDEX_BATCH_SIZE):
        batch_ids = pending_ids[start : start + INDEX_BATCH_SIZE]
        with _index_lock:
            records = session.scalars(
                select(CustomerRecord).where(CustomerRecord.customer_id.in_(batch_ids))
            ).all()
            if not records:
                continue
            documents = [customer_record_document(record) for record in records]
            record_ids = [record.customer_id for record in records]
            vector_store.add_documents(documents=documents, ids=record_ids)
        indexed_count += len(record_ids)
        logger.info("Added %s customer records to the RAG index.", indexed_count)

    logger.info("RAG index startup sync added %s missing customer records.", indexed_count)
    return indexed_count


def _sync_database_index_in_background() -> None:
    with SessionLocal() as session:
        sync_database_index(session)


def start_database_index_sync() -> None:
    """Start missing-profile embedding without delaying API health or requests."""
    thread = Thread(
        target=_sync_database_index_in_background,
        name="rag-database-index-sync",
        daemon=True,
    )
    thread.start()


def sync_customer_record(record: CustomerRecord) -> None:
    """Keep every saved profile, including synthetic examples, searchable."""
    upsert_customer_document(record)


def upsert_customer_document(record: CustomerRecord) -> None:
    """Index the latest saved profile, replacing any older document for its ID."""
    try:
        with _index_lock:
            get_vector_store().add_documents(
                documents=[customer_record_document(record)],
                ids=[record.customer_id],
            )
    except Exception as error:
        logger.exception("Failed to sync customer %s to the RAG index.", record.customer_id)
        raise RagIndexSyncError(
            f"Could not update the RAG document for customer {record.customer_id}."
        ) from error


def delete_customer_document(customer_id: str) -> None:
    """Remove a deleted profile from the semantic-search index."""
    try:
        with _index_lock:
            get_vector_store().delete(ids=[customer_id])
    except Exception as error:
        logger.exception("Failed to remove customer %s from the RAG index.", customer_id)
        raise RagIndexSyncError(
            f"Could not remove the RAG document for customer {customer_id}."
        ) from error


def build_versioned_index(
    dataset: pd.DataFrame,
    collection_name: str | None = None,
) -> tuple[Chroma, str]:
    """Build an index under a fresh collection, preserving the active one."""
    settings = get_settings()
    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    selected_name = collection_name or f"{COLLECTION_PREFIX}{uuid4().hex[:16]}"
    vector_store = Chroma.from_documents(
        documents=make_customer_documents(dataset),
        embedding=get_embeddings(),
        ids=dataset["customer_id"].astype(str).tolist(),
        collection_name=selected_name,
        persist_directory=str(settings.chroma_path),
    )
    return vector_store, selected_name


def activate_collection(collection_name: str) -> None:
    """Atomically switch the collection name used by the RAG service."""
    global _vector_store
    settings = get_settings()
    manifest_path: Path = settings.chroma_collection_path
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = manifest_path.with_suffix(".tmp")
    temporary_path.write_text(collection_name, encoding="utf-8")
    temporary_path.replace(manifest_path)
    with _vector_store_lock:
        _vector_store = None


def active_collection_name() -> str:
    """Read the active Chroma collection, falling back to the original name."""
    manifest_path = get_settings().chroma_collection_path
    if not manifest_path.is_file():
        return "telco_customer_churn"
    collection_name = manifest_path.read_text(encoding="utf-8").strip()
    return collection_name or "telco_customer_churn"
