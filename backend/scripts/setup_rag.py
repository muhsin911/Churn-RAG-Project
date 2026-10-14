"""Create or update a persistent ChromaDB index for customer churn records."""

import sys
from pathlib import Path

from langchain_core.documents import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils.data_loader import load_telco_data
from app.services.rag_index_service import (
    activate_collection,
    build_versioned_index,
    make_customer_documents,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
CHROMA_PATH = BACKEND_DIR / "chroma_db"


def load_customer_documents() -> list[Document]:
    """Convert each validated CSV row into a searchable LangChain document."""
    return make_customer_documents(load_telco_data())


def main() -> None:
    """Embed customer documents locally and persist them in ChromaDB."""
    dataset = load_telco_data()
    _, collection_name = build_versioned_index(dataset)
    activate_collection(collection_name)

    print(f"Indexed {len(dataset):,} customer documents.")
    print(f"ChromaDB collection: {collection_name}")
    print("Embeddings: local sentence-transformers/all-MiniLM-L6-v2")
    print(f"Persistent storage: {CHROMA_PATH}")


if __name__ == "__main__":
    main()