"""
RAG system using remote collections from Albert API
avec reranking Albert intégré.
"""

from typing import List, Dict, Optional, Tuple
from openai import OpenAI
import os

from config.rag_config import get_rag_config
from services.api_reranker import get_reranker_service


# -------------------------------------------------------------------------
# Utils
# -------------------------------------------------------------------------

def get_collection_id(client: OpenAI, collection_name: str) -> Optional[int]:
    """Récupère l'ID d'une collection à partir de son nom."""
    api_key = os.getenv("API-KEY")
    headers = {"Authorization": f"Bearer {api_key}"}

    offset = 0
    limit = 100

    while True:
        response = client._client.request(
            method="GET",
            url="/collections",
            params={"offset": offset, "limit": limit},
            headers=headers,
        )

        if response.status_code != 200:
            print(f"❌ Erreur récupération collections: {response.status_code}")
            return None

        data = response.json()
        collections = data.get("data", [])

        if not collections:
            break

        for col in collections:
            if col.get("name") == collection_name:
                cid = col.get("id")
                print(f"   ✅ Collection '{collection_name}' trouvée avec ID: {cid}")
                return cid

        offset += limit

    print(f"   ❌ Collection '{collection_name}' non trouvée")
    return None


# -------------------------------------------------------------------------
# Search
# -------------------------------------------------------------------------

def query_remote_collection(
    client: OpenAI,
    collection_name: str,
    query: str,
    top_k: Optional[int] = None,
    method: str = "hybrid",
    score_threshold: float = 0.0,
) -> List[Dict]:
    """Interroge une collection distante via Albert /search."""
    config = get_rag_config()

    if not top_k:
        top_k = config.retrieval.top_k

    print(f"   🔧 Top K utilisé: {top_k}")
    print(f"   🔍 Méthode de recherche: {method}")

    collection_id = get_collection_id(client, collection_name)
    if collection_id is None:
        return []

    api_key = os.getenv("API-KEY")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "collections": [collection_id],
        "prompt": query,
        "limit": top_k,
        "method": method,
        "score_threshold": score_threshold,
        "offset": 0,
    }

    print("   📡 Appel API: POST /search")
    print(f"   📦 Payload: {payload}")

    response = client._client.request(
        method="POST",
        url="/search",
        json=payload,
        headers=headers,
    )

    print(f"   ✅ Réponse API reçue (status: {response.status_code})")

    if response.status_code != 200:
        print(response.text)
        return []

    results = response.json()
    data_items = results.get("data", [])

    print(f"   📊 {len(data_items)} résultats reçus")

    documents = []

    for idx, item in enumerate(data_items):
        chunk = item.get("chunk", {})
        text = chunk.get("content", "") if isinstance(chunk, dict) else str(chunk)

        document = {
            "id": item.get("id"),
            "score": item.get("score", 0.0),
            "text": text,
            "filename": chunk.get("metadata", {}).get("filename"),
            "chunk_id": chunk.get("id"),
            "model": "remote",
            "search_method": method,
        }

        documents.append(document)
        print(f"   📄 Doc {idx+1}: score={document['score']:.3f}, len={len(text)} chars")

    return documents


# -------------------------------------------------------------------------
# RAG Context + Reranking
# -------------------------------------------------------------------------

def build_rag_context_from_remote(
    client: OpenAI,
    collection_name: str,
    query: str,
    top_k: Optional[int] = None,
    max_tokens: Optional[int] = None,
    method: str = "hybrid",
) -> Optional[Tuple[Dict, List[Dict]]]:
    """Construit le contexte RAG avec reranking Albert."""
    config = get_rag_config()

    if max_tokens is None:
        max_tokens = config.context.max_tokens

    print(f"\n🔍 [RAG Remote] Recherche dans collection: {collection_name}")
    print(f"   Query: {query}")
    print(f"   Top K: {top_k}")
    print(f"   Method: {method}")

    docs = query_remote_collection(
        client=client,
        collection_name=collection_name,
        query=query,
        top_k=top_k,
        method=method,
    )

    if not docs:
        print("   ⚠️ Aucun document trouvé")
        return None

    # ------------------------------------------------------------------
    # 🔁 RERANKING
    # ------------------------------------------------------------------
    try:
        print("\n🔁 Application du reranker Albert...")

        reranker = get_reranker_service(client)

        texts = [d["text"] for d in docs]

        reranked = reranker.rerank(
            query=query,
            documents=texts,
            model=config.models.reranking_model,
            top_n=config.reranking.top_n,
        )

        docs = [docs[r["index"]] for r in reranked]

        print(f"   ✅ Reranking appliqué ({len(docs)} documents)")

    except Exception as e:
        print(f"⚠️ Reranking échoué, fallback search-only: {e}")

    # ------------------------------------------------------------------
    # Construction du contexte
    # ------------------------------------------------------------------
    context_blocks = []
    total_tokens = 0

    for d in docs:
        source = (
            f"{d.get('filename', 'Document')} "
            f"# chunk {d.get('chunk_id', '?')} "
            f"# score {round(d.get('score', 0.0), 3)}"
        )

        block = f"{source}\n{d.get('text', '')}"
        block_tokens = len(block) // 4

        if total_tokens + block_tokens > max_tokens:
            print(f"   ⚠️ Budget tokens atteint ({total_tokens}/{max_tokens})")
            break

        context_blocks.append(block)
        total_tokens += block_tokens

    if not context_blocks:
        print("   ⚠️ Aucun contexte construit")
        return None

    context = "\n\n".join(context_blocks)
    content = config.context.system_template.format(context=context)

    system_message = {
        "role": "system",
        "content": content,
    }

    print(f"   ✅ Contexte RAG créé ({len(context_blocks)} blocs, {total_tokens} tokens)")
    print(f"   📝 Aperçu contexte: {content[:200]}...")

    return system_message, docs
