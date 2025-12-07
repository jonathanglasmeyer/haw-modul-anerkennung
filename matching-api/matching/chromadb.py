"""ChromaDB setup with Gemini embeddings."""
import os
import chromadb
from google import genai
from datetime import datetime
from typing import Optional
from .database import fetch_units_from_db, get_units_checksum

EMBEDDING_MODEL = "gemini-embedding-001"
COLLECTION_NAME = "units"

# Gemini client (lazy loaded)
_genai_client = None


def get_genai_client():
    """Get or create Gemini client."""
    global _genai_client
    if _genai_client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable required")
        _genai_client = genai.Client(api_key=api_key)
    return _genai_client


class GeminiEmbeddingFunction:
    """Custom embedding function using Gemini API."""

    def name(self) -> str:
        """Return the name of this embedding function."""
        return "gemini-embedding"

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for input texts."""
        client = get_genai_client()
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=texts,
        )
        return [e.values for e in result.embeddings]

    def __call__(self, input: list[str]) -> list[list[float]]:
        """Generate embeddings for input texts."""
        return self._embed(input)

    def embed_documents(self, input: list[str]) -> list[list[float]]:
        """Embed documents for storage."""
        return self._embed(input)

    def embed_query(self, input: str) -> list[list[float]]:
        """Embed a single query for search."""
        return self._embed([input])


# Cached client and collection
_client = None
_collection = None

# Cache last known checksum to avoid redundant syncs
_last_checksum: Optional[datetime] = None


def get_vectorstore(vectorstore_path: str = None):
    """Get or create ChromaDB collection."""
    global _client, _collection

    if _collection is not None:
        return _collection

    # Persistent storage for production
    if os.getenv("CHROMADB_PERSISTENT"):
        persist_dir = vectorstore_path or os.getenv("VECTORSTORE_PATH", "./data/vectorstore")
        _client = chromadb.PersistentClient(path=persist_dir)
    else:
        _client = chromadb.Client()

    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=GeminiEmbeddingFunction(),
        metadata={"hnsw:space": "cosine"}
    )

    return _collection


def sync_from_database(force_refresh: bool = False) -> int:
    """Sync units from NeonDB into ChromaDB.

    Args:
        force_refresh: Force full refresh of ChromaDB collection

    Returns:
        Number of units in collection
    """
    # Fetch from NeonDB
    data = fetch_units_from_db()
    units = data.get("units", {})
    modules = data.get("modules", {})

    if not units:
        print("No units to load")
        return 0

    collection = get_vectorstore()

    # Check what needs to be updated (partial sync)
    existing = collection.get()
    existing_ids = set(existing["ids"]) if existing["ids"] else set()
    new_ids = set(units.keys())

    to_add = new_ids - existing_ids
    to_delete = existing_ids - new_ids

    if not to_add and not to_delete and not force_refresh:
        print(f"ChromaDB up to date ({len(existing_ids)} units)")
        return len(existing_ids)

    # Delete removed units
    if to_delete:
        collection.delete(ids=list(to_delete))
        print(f"Deleted {len(to_delete)} removed units")

    # Only process new/changed units
    if force_refresh:
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
            print(f"Force refresh: cleared {len(existing['ids'])} units")
        units_to_process = units
    else:
        units_to_process = {uid: units[uid] for uid in to_add}
        if units_to_process:
            print(f"Adding {len(units_to_process)} new units...")

    if not units_to_process:
        total = collection.count()
        print(f"No new units to add. Total: {total}")
        return total

    documents = []
    metadatas = []
    ids = []

    for unit_id, unit in units_to_process.items():
        module_id = unit.get("module_id", "")
        module = modules.get(module_id, {})

        # Build searchable text content
        content_parts = [
            f"Unit: {unit.get('title', '')}",
            f"Modul: {module.get('title', '')}",
        ]

        if unit.get("learning_outcomes_text"):
            content_parts.append(f"Lernziele:\n{unit['learning_outcomes_text']}")

        if unit.get("content"):
            content_parts.append(f"Inhalte:\n{unit['content']}")

        if module.get("gesamtziele"):
            content_parts.append(f"Modulziele:\n{module['gesamtziele']}")

        document = "\n\n".join(content_parts)

        # Metadata for filtering and display
        verantwortliche = unit.get("verantwortliche", [])
        metadata = {
            "unit_id": unit_id,
            "unit_title": unit.get("title", ""),
            "module_id": module_id,
            "module_title": module.get("title", ""),
            "semester": str(unit.get("semester", "")),
            "sws": str(unit.get("sws", "")),
            "credits": str(module.get("credits", "")),
            "workload": str(unit.get("workload", "")),
            "lehrsprache": str(unit.get("lehrsprache", "")),
            "pruefungsleistung": str(module.get("pruefungsleistung", ""))[:200],
            "studiengang": "BAPuMa",
            "verantwortliche": ", ".join(verantwortliche) if verantwortliche else "",
        }

        documents.append(document)
        metadatas.append(metadata)
        ids.append(unit_id)

    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

    total = collection.count()
    print(f"Added {len(documents)} units. Total: {total}")
    return total


def ensure_synced() -> bool:
    """
    Ensure ChromaDB is synced with latest NeonDB data.

    Uses checksum (max updated_at timestamp) to detect changes.
    Only syncs if data changed since last check.

    Returns:
        True if sync was performed, False if already up-to-date
    """
    global _last_checksum

    current_checksum = get_units_checksum()

    # First run or data changed
    if _last_checksum is None or current_checksum != _last_checksum:
        print(f"Units checksum changed: {_last_checksum} -> {current_checksum}")
        sync_from_database()
        _last_checksum = current_checksum
        return True

    return False
