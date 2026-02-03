from typing import List, Dict
from services.albert_collections import AlbertCollectionsClient

_albert_client = AlbertCollectionsClient()


def retrieve_remote_docs(
    collection_id: str,
    query: str,
    top_k: int
) -> List[Dict]:
    """
    Recherche sémantique dans une collection distante Albert.
    L'embedding est fait côté serveur Albert.
    """

    results = _albert_client.search(
        collection_id=collection_id,
        query=query,
        limit=top_k
    )

    docs = []
    for r in results:
        docs.append({
            "id": r.get("id"),
            "score": float(r.get("score", 0.0)),
            "text": r.get("text", ""),
            "filename": r.get("metadata", {}).get("filename"),
            "filepath": r.get("metadata", {}).get("filepath"),
            "chunk_id": r.get("metadata", {}).get("chunk_id"),
            "source": "remote",
            "model": "albert",
        })

    return docs
