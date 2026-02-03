import os

try:
    from qdrant_client import QdrantClient
except ImportError:
    QdrantClient = None


from config.settings import (
    QDRANT_HOST,
    QDRANT_PORT,
    QDRANT_API_KEY
)

qdrant_available = False
qdrant_client = None
qdrant_collections = []


if QdrantClient:
    try:
        try:
            qdrant_client = QdrantClient(
                host=QDRANT_HOST,
                port=QDRANT_PORT,
                api_key=QDRANT_API_KEY
            )
        except Exception:
            qdrant_client = QdrantClient(
                url=f"http://{QDRANT_HOST}:{QDRANT_PORT}",
                api_key=QDRANT_API_KEY
            )

        colls = qdrant_client.get_collections()
        if hasattr(colls, "collections"):
            qdrant_collections = [c.name for c in colls.collections]
        else:
            qdrant_collections = [c["name"] for c in colls["collections"]]

        qdrant_available = True

    except Exception:
        qdrant_available = False

# Plante sur qdrant-client >=1.6.0 A revoir pour plus tard
def search_qdrant(query: str, collection: str, top_k: int = 20):
    """
    Recherche vectorielle simple dans Qdrant.
    Retourne une liste de dicts normalisés pour le RAG.
    """
    if not qdrant_available or not qdrant_client:
        return []

    results = qdrant_client.search(
        collection_name=collection,
        query_vector=query,  # ⚠️ suppose un Qdrant avec embedding server-side
        limit=top_k,
        with_payload=True
    )

    docs = []

    for r in results:
        payload = r.payload or {}

        docs.append({
            "content": payload.get("content", ""),
            "filename": payload.get("filename"),
            "score": r.score
        })

    return docs
