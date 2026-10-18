"""API tests for the health, prediction, and chat endpoints."""

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pandas as pd
import pytest

from app.main import app
from app.models.schemas import ChatResponse
from app.routes import chat
from app.routes.predict import router as prediction_router
from app.utils.data_loader import load_telco_data
from scripts.train_model import FEATURE_COLUMNS, train_pipeline


TELCO_CSV = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "raw"
    / "WA_Fn-UseC_-Telco-Customer-Churn.csv"
)


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def prediction_client() -> Iterator[TestClient]:
    prediction_app = FastAPI()
    prediction_app.include_router(prediction_router)
    with TestClient(prediction_app) as test_client:
        yield test_client


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_prediction_endpoint_uses_trained_pipeline(
    prediction_client: TestClient,
) -> None:
    response = prediction_client.post(
        "/predict",
        json={
            "tenure": 12,
            "monthly_charges": 70.0,
            "total_charges": 840.0,
            "senior_citizen": 0,
            "gender": "Female",
            "partner": "No",
            "dependents": "No",
            "phone_service": "Yes",
            "multiple_lines": "No",
            "internet_service": "Fiber optic",
            "online_security": "No",
            "online_backup": "No",
            "device_protection": "No",
            "tech_support": "No",
            "streaming_tv": "No",
            "streaming_movies": "No",
            "contract_type": "Month-to-month",
            "paperless_billing": "Yes",
            "payment_method": "Electronic check",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["churn_prediction"], bool)
    assert 0 <= body["churn_probability"] <= 1
    assert body["message"]
    assert body["explanations"]
    assert {
        "Tenure",
        "Monthly charges",
        "Total charges",
        "Senior citizen",
        "Gender",
        "Partner",
        "Dependents",
        "Phone service",
        "Multiple lines",
        "Internet service",
        "Online security",
        "Online backup",
        "Device protection",
        "Tech support",
        "Streaming TV",
        "Streaming movies",
        "Contract type",
        "Paperless billing",
        "Payment method",
    } == {item["feature"] for item in body["explanations"]}
    assert abs(
        body["baseline_probability"]
        + sum(item["impact"] for item in body["explanations"])
        - body["churn_probability"]
    ) < 1e-6


def test_prediction_endpoint_rejects_invalid_contract(
    prediction_client: TestClient,
) -> None:
    response = prediction_client.post(
        "/predict",
        json={
            "tenure": 12,
            "monthly_charges": 70.0,
            "contract_type": "Monthly",
            "payment_method": "Electronic check",
        },
    )

    assert response.status_code == 422


def test_prediction_endpoint_handles_omitted_optional_profile_fields(
    prediction_client: TestClient,
) -> None:
    response = prediction_client.post(
        "/predict",
        json={
            "tenure": 12,
            "monthly_charges": 70.0,
            "contract_type": "Month-to-month",
            "payment_method": "Electronic check",
        },
    )

    assert response.status_code == 200
    assert len(response.json()["explanations"]) == 19


def test_chat_endpoint_returns_answer_and_sources(
    client: TestClient,
    monkeypatch,
) -> None:
    def fake_chat_with_data(question: str) -> ChatResponse:
        assert question == "Which customers churned?"
        return ChatResponse(answer="Some indexed customers churned.", sources=["CUST-0001"])

    monkeypatch.setattr(chat, "chat_with_data", fake_chat_with_data)
    response = client.post("/chat", json={"question": "Which customers churned?"})

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Some indexed customers churned.",
        "sources": ["CUST-0001"],
    }


def test_synthetic_customer_is_indexed_and_cited_as_synthetic(monkeypatch) -> None:
    from types import SimpleNamespace

    from langchain_core.documents import Document

    from app.services import rag_index_service
    from app.services.rag_service import _format_source

    indexed_ids: list[str] = []
    record = SimpleNamespace(customer_id="SYN-TEST", record_source="synthetic")
    monkeypatch.setattr(
        rag_index_service,
        "upsert_customer_document",
        lambda customer: indexed_ids.append(customer.customer_id),
    )

    rag_index_service.sync_customer_record(record)
    source = _format_source(
        Document(
            page_content="Synthetic profile example.",
            metadata={"customer_id": "SYN-TEST", "record_source": "synthetic"},
        )
    )

    assert indexed_ids == ["SYN-TEST"]
    assert source == "SYN-TEST (synthetic example)"


def test_startup_index_sync_includes_synthetic_database_rows(monkeypatch) -> None:
    from types import SimpleNamespace

    from app.models.customer import CustomerRecord
    from app.services import rag_index_service

    row_values = {
        column.name: None for column in CustomerRecord.__table__.columns
    }
    row_values.update(
        {
            "customer_id": "SYN-STARTUP",
            "tenure": 12,
            "monthly_charges": 70.0,
            "total_charges": 840.0,
            "contract_type": "Month-to-month",
            "payment_method": "Electronic check",
            "senior_citizen": 0,
            "record_source": "synthetic",
        }
    )
    record = SimpleNamespace(**row_values)

    class FakeScalars:
        def __init__(self, values):
            self.values = values

        def all(self):
            return self.values

    class FakeSession:
        calls = 0

        def scalars(self, statement):
            self.calls += 1
            values = ["SYN-STARTUP"] if self.calls == 1 else [record]
            return FakeScalars(values)

    class FakeVectorStore:
        ids: list[str] = []
        documents = []

        def get(self, include):
            return {"ids": self.ids}

        def add_documents(self, documents, ids):
            self.documents.extend(documents)
            self.ids.extend(ids)

    vector_store = FakeVectorStore()
    monkeypatch.setattr(
        rag_index_service,
        "get_vector_store",
        lambda: vector_store,
    )

    indexed_count = rag_index_service.sync_database_index(FakeSession())

    assert indexed_count == 1
    assert vector_store.ids == ["SYN-STARTUP"]
    assert vector_store.documents[0].metadata["record_source"] == "synthetic"


def test_ollama_provider_uses_configured_local_model(monkeypatch) -> None:
    import sys
    from types import SimpleNamespace

    from app.config import get_settings
    from app.services import rag_service

    settings = get_settings()
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "ollama_model", "test-local-model")
    monkeypatch.setattr(settings, "ollama_base_url", "http://localhost:11434")

    class FakeChatOllama:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

    class FakeVectorStore:
        def get(self, limit: int) -> dict[str, list[str]]:
            return {"ids": ["test-customer"]}

        def as_retriever(self, search_kwargs: dict[str, int]) -> object:
            return object()

    fake_vector_store = FakeVectorStore()
    captured: dict[str, object] = {}
    monkeypatch.setitem(
        sys.modules,
        "langchain_ollama",
        SimpleNamespace(ChatOllama=FakeChatOllama),
    )
    monkeypatch.setattr(rag_service, "get_vector_store", lambda: fake_vector_store)
    monkeypatch.setattr(
        rag_service,
        "DatasetEvidenceRetriever",
        lambda customer_retriever: object(),
    )
    monkeypatch.setattr(
        rag_service,
        "RetrievalQA",
        SimpleNamespace(
            from_chain_type=lambda **kwargs: (
                captured.update(kwargs) or kwargs["llm"]
            )
        ),
    )
    rag_service._load_qa_chain.cache_clear()
    try:
        model = rag_service._load_qa_chain()
    finally:
        rag_service._load_qa_chain.cache_clear()

    assert isinstance(model, FakeChatOllama)
    assert model.kwargs == {
        "model": "test-local-model",
        "base_url": "http://localhost:11434",
        "temperature": 0,
    }
    assert captured["chain_type"] == "stuff"


def test_telco_data_cleaning_handles_zero_tenure_blank_charges() -> None:
    dataset = load_telco_data(TELCO_CSV)

    assert len(dataset) == 7_043
    assert dataset["customer_id"].is_unique
    assert dataset["total_charges"].notna().all()
    assert dataset.loc[dataset["tenure"].eq(0), "total_charges"].eq(0).all()
    assert set(dataset["churn_label"].unique()) == {0, 1}


def test_training_pipeline_uses_all_customer_profile_features() -> None:
    dataset = load_telco_data(TELCO_CSV).sample(n=1_000, random_state=42)

    model, _ = train_pipeline(dataset)

    assert len(FEATURE_COLUMNS) == 19
    assert list(model.feature_names_in_) == FEATURE_COLUMNS
    assert not {"customer_id", "churn_label"}.intersection(FEATURE_COLUMNS)


def test_stored_customer_prediction_passes_all_profile_features(monkeypatch) -> None:
    from types import SimpleNamespace

    from app.models.schemas import PredictionResponse
    from app.services import customer_service

    profile = {
        "tenure": 12,
        "monthly_charges": 70.0,
        "total_charges": 840.0,
        "senior_citizen": 0,
        "gender": "Female",
        "partner": "No",
        "dependents": "No",
        "phone_service": "Yes",
        "multiple_lines": "No",
        "internet_service": "Fiber optic",
        "online_security": "No",
        "online_backup": "No",
        "device_protection": "No",
        "tech_support": "No",
        "streaming_tv": "No",
        "streaming_movies": "No",
        "contract_type": "Month-to-month",
        "paperless_billing": "Yes",
        "payment_method": "Electronic check",
    }
    record = SimpleNamespace(
        customer_id="MAN-TEST",
        predicted_churn=None,
        churn_probability=None,
        **profile,
    )
    captured: dict[str, object] = {}
    result = PredictionResponse(
        churn_prediction=False,
        churn_probability=0.2,
        message="This customer is predicted to stay.",
        baseline_probability=0.2,
        explanations=[],
    )

    class FakeSession:
        def commit(self):
            pass

        def refresh(self, customer):
            pass

    def fake_predict(features):
        captured.update(features.model_dump())
        return result

    monkeypatch.setattr(customer_service, "get_customer", lambda session, customer_id: record)
    monkeypatch.setattr(customer_service, "predict_churn", fake_predict)

    saved_record, prediction = customer_service.predict_customer_by_id(
        FakeSession(), "MAN-TEST"
    )

    assert saved_record is record
    assert prediction is result
    assert set(captured) == set(FEATURE_COLUMNS)
    assert captured == profile


def test_telco_data_cleaning_rejects_missing_nonzero_tenure_charges(
    tmp_path: Path,
) -> None:
    source = pd.read_csv(TELCO_CSV).head(2)
    source.loc[0, "TotalCharges"] = " "
    invalid_csv = tmp_path / "invalid-charges.csv"
    source.to_csv(invalid_csv, index=False)

    try:
        load_telco_data(invalid_csv)
    except ValueError as error:
        assert "non-zero tenure" in str(error)
    else:
        raise AssertionError("Missing charges for a current customer were accepted.")


def test_analytics_summary_uses_full_dataset_counts(client: TestClient) -> None:
    response = client.get("/analytics/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["total_customers"] >= 30_000
    assert body["known_actual_outcomes"] >= 7_043
    assert body["unlabeled_customers"] == (
        body["total_customers"] - body["known_actual_outcomes"]
    )
    assert body["churn_count"] + body["retained_count"] == (
        body["known_actual_outcomes"]
    )
    assert body["churn_rate"] == body["churn_count"] / body["known_actual_outcomes"]
    assert body["segments"]


def test_rag_database_evidence_excludes_unknown_outcomes(
    client: TestClient,
) -> None:
    from app.services.analytics_service import format_dataset_evidence

    summary = client.get("/analytics/summary").json()
    evidence = format_dataset_evidence(summary)

    assert "Customer profiles: 30000" in evidence
    assert "known actual outcomes: 7043" in evidence
    assert "outcomes not yet known: 22957" in evidence
    assert "Churned: 1869; retained: 5174" in evidence
    assert "churn rate among known outcomes: 26.5%" in evidence


def test_customer_crud_prediction_and_delete_workflow(client: TestClient) -> None:
    from app.services.rag_index_service import get_vector_store

    customer_id = f"TEST-{uuid4().hex[:12].upper()}"
    created = client.post(
        "/customers",
        json={
            "customer_id": customer_id,
            "tenure": 12,
            "monthly_charges": 70.0,
            "total_charges": 840.0,
            "contract_type": "Month-to-month",
            "payment_method": "Electronic check",
            "actual_churn": None,
        },
    )
    assert created.status_code == 201
    assert created.json()["actual_churn"] is None
    assert created.json()["predicted_churn"] is None
    created_document = get_vector_store().get(ids=[customer_id])
    assert created_document["ids"] == [customer_id]
    assert "Actual churn outcome: Unknown" in created_document["documents"][0]

    fetched = client.get(f"/customers/{customer_id}")
    assert fetched.status_code == 200
    assert fetched.json()["customer_id"] == customer_id

    page = client.get("/customers?page=1&page_size=10&search=" + customer_id)
    assert page.status_code == 200
    assert page.json()["total"] == 1
    assert page.json()["items"][0]["customer_id"] == customer_id

    prediction = client.post(f"/customers/{customer_id}/predict")
    assert prediction.status_code == 200
    assert 0 <= prediction.json()["churn_probability"] <= 1
    saved_prediction = client.get(f"/customers/{customer_id}").json()
    assert isinstance(saved_prediction["predicted_churn"], bool)
    assert saved_prediction["churn_probability"] == prediction.json()["churn_probability"]
    assert saved_prediction["actual_churn"] is None

    updated = client.patch(
        f"/customers/{customer_id}",
        json={"actual_churn": True},
    )
    assert updated.status_code == 200
    assert updated.json()["actual_churn"] is True
    assert updated.json()["predicted_churn"] is not None
    updated_document = get_vector_store().get(ids=[customer_id])
    assert "Actual churn outcome: Yes" in updated_document["documents"][0]

    replaced = client.put(
        f"/customers/{customer_id}",
        json={
            "tenure": 24,
            "monthly_charges": 80.0,
            "total_charges": 1920.0,
            "contract_type": "One year",
            "payment_method": "Credit card",
        },
    )
    assert replaced.status_code == 200
    assert replaced.json()["tenure"] == 24
    assert replaced.json()["actual_churn"] is True
    assert replaced.json()["predicted_churn"] is None

    deleted = client.delete(f"/customers/{customer_id}")
    assert deleted.status_code == 204
    assert client.get(f"/customers/{customer_id}").status_code == 404
    assert get_vector_store().get(ids=[customer_id])["ids"] == []


def test_startup_rag_index_contains_seeded_database_customers(
    client: TestClient,
) -> None:
    from app.services.rag_index_service import get_vector_store

    indexed_ids = get_vector_store().get(include=[])["ids"]
    assert len(indexed_ids) >= 7_043