"""Retrieve relevant customer records and answer questions about them."""

from functools import lru_cache
from typing import Any

from langchain_classic.chains import RetrievalQA
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_core.retrievers import BaseRetriever

from app.config import get_settings
from app.db import SessionLocal
from app.models.schemas import ChatResponse
from app.services.analytics_service import format_dataset_evidence
from app.services.customer_service import get_customer_database_summary
from app.services.rag_index_service import get_vector_store


class DatasetEvidenceRetriever(BaseRetriever):
    """Add exact whole-dataset calculations to semantic customer retrieval."""

    customer_retriever: BaseRetriever

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        """Retrieve examples for the question alongside exact dataset evidence."""
        customer_documents = self.customer_retriever.invoke(
            query,
            config={"callbacks": run_manager.get_child()},
        )
        with SessionLocal() as session:
            summary = get_customer_database_summary(session).model_dump()
        return [
            Document(
                page_content=format_dataset_evidence(summary),
                metadata={"source": "computed_dataset_summary"},
            ),
            *customer_documents,
        ]


@lru_cache(maxsize=1)
def _load_qa_chain() -> RetrievalQA:
    """Load the persisted Chroma collection and configure its answer chain."""
    settings = get_settings()
    if not settings.chroma_path.is_dir():
        raise FileNotFoundError(
            f"ChromaDB data not found at {settings.chroma_path}. "
            "Run `python scripts/setup_rag.py` from the backend directory first."
        )
    vector_store = get_vector_store()
    if not vector_store.get(limit=1)["ids"]:
        raise ValueError(
            "The active ChromaDB collection is empty. "
            "Run `python scripts/setup_rag.py` to index the dataset."
        )

    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=settings.openai_api_key,
        )
    elif settings.llm_provider == "groq":
        from langchain_groq import ChatGroq

        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is required when LLM_PROVIDER=groq.")
        llm = ChatGroq(
            model="openai/gpt-oss-120b",
            temperature=0,
            api_key=settings.groq_api_key,
        )
    else:
        from langchain_ollama import ChatOllama

        llm = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0,
        )

    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=(
            "You are a careful customer churn data analyst. Answer using the "
            "exact dataset statistics and retrieved customer records in the "
            "context. Distinguish calculated facts from hypotheses. For churn "
            "examples, clearly identify records marked synthetic as simulated, "
            "not observed customers or factual outcomes. Never treat synthetic "
            "records as labeled evidence. For churn "
            "rates, use the "
            "provided rate among known actual outcomes; never divide churned "
            "customers by all profiles when some outcomes are unknown. State "
            "that unknown outcomes are excluded from the rate. Do not say "
            "that an association causes churn. For retention recommendations, "
            "suggest practical experiments tied to observed high-churn segments "
            "and say their effects must be measured. If the context does not "
            "contain enough evidence, say so.\n\n"
            "Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        ),
    )
    retriever = DatasetEvidenceRetriever(
        customer_retriever=vector_store.as_retriever(search_kwargs={"k": 4})
    )
    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )


def _format_source(document: Document) -> str:
    """Make a readable citation from a retrieved customer document."""
    customer_id = document.metadata.get("customer_id")
    if not customer_id:
        return "Dataset-wide computed statistics"
    if document.metadata.get("record_source") == "synthetic":
        return f"{customer_id} (synthetic example)"
    return str(customer_id)


def chat_with_data(question: str) -> ChatResponse:
    """Answer a natural-language question using retrieved churn records."""
    chain = _load_qa_chain()
    result: dict[str, Any] = chain.invoke({"query": question})
    answer = result.get("result")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("The RAG chain returned an empty answer.")

    source_documents = result.get("source_documents", [])
    sources = [
        _format_source(document)
        for document in source_documents
        if isinstance(document, Document)
    ]
    return ChatResponse(answer=answer.strip(), sources=sources)