"""RAG system with API embeddings and reranking."""
from typing import List, Dict, Optional, Callable, Set
from collections import defaultdict
from openai import OpenAI
import re
import html

from services.qdrant import qdrant_client
from services.api_embeddings import get_embedding_service
from services.api_reranker import get_reranker_service
from config.rag_config import get_rag_config


class RAGLogger:
    """Logger abstrait pour le système RAG."""

    def __init__(
        self,
        warning_callback: Optional[Callable[[str], None]] = None,
        error_callback: Optional[Callable[[str], None]] = None
    ):
        self.warning = warning_callback or (lambda msg: print(f"WARNING: {msg}"))
        self.error = error_callback or (lambda msg: print(f"ERROR: {msg}"))


# Logger global
_rag_logger = RAGLogger()


def set_rag_logger(logger: RAGLogger):
    """Configure le logger pour le système RAG."""
    global _rag_logger
    _rag_logger = logger


def highlight_relevant_sentences(text: str, query: str) -> str:
    """Highlight relevant sentences in text based on query."""
    config = get_rag_config()

    if not text or not query:
        return html.escape(text or "")

    if not config.highlighting.highlight_sentences:
        return html.escape(text)

    query_words = {
        w.lower()
        for w in re.findall(r"\w+", query)
        if len(w) >= config.highlighting.min_word_length
    }

    sentences = re.split(r"(?<=[.!?])\s+", text)
    highlighted = []

    for s in sentences:
        s_lower = s.lower()
        if any(w in s_lower for w in query_words):
            escaped = html.escape(s)
            for w in sorted(query_words, key=len, reverse=True):
                escaped = re.sub(
                    re.escape(w),
                    r"<mark>\g<0></mark>",
                    escaped,
                    flags=re.IGNORECASE
                )
            color = config.highlighting.highlight_color
            highlighted.append(f"<mark style='background:{color}'>{escaped}</mark>")
        else:
            highlighted.append(html.escape(s))

    return " ".join(highlighted)


def retrieve_relevant_docs(
    collection: str,
    query: str,
    openai_client: OpenAI,
    top_k: Optional[int] = None,
    min_score: Optional[float] = None,
    embedding_model: Optional[str] = None
) -> List[Dict]:
    """
    Retrieve relevant documents using API embeddings.

    Args:
        collection: Nom de la collection Qdrant
        query: Requête de recherche
        openai_client: Client OpenAI pour les embeddings
        top_k: Nombre de documents à récupérer
        min_score: Score minimum
        embedding_model: Modèle d'embedding (utilise config si None)
    """
    config = get_rag_config()

    if top_k is None:
        top_k = config.retrieval.top_k
    if min_score is None:
        min_score = config.retrieval.min_score
    if embedding_model is None:
        embedding_model = config.models.embedding_model

    # Récupérer le service d'embeddings
    embedding_service = get_embedding_service(openai_client)

    # Encoder la requête avec le modèle configuré
    query_vector = embedding_service.encode_query(query, embedding_model)

    # Rechercher dans Qdrant
    if hasattr(qdrant_client, "query_points"):
        results = qdrant_client.query_points(
            collection_name=collection,
            query=query_vector,
            limit=top_k,
            with_payload=True,
            with_vectors=False
        ).points
    else:
        results = qdrant_client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True
        )

    # Traiter les résultats
    docs = []
    for r in results:
        score = getattr(r, "score", None)
        distance = getattr(r, "distance", None)

        if score is None and distance is not None:
            score = 1 - distance

        if score is not None and score < min_score:
            continue

        p = r.payload or {}
        docs.append({
            "id": r.id,
            "score": float(score) if score is not None else 0.0,
            "text": p.get("text", ""),
            "filename": p.get("filename"),
            "filepath": p.get("filepath"),
            "chunk_id": p.get("chunk_id"),
            "model": embedding_model
        })

    return docs


def get_chunk_by_id(
    collection: str,
    filepath: str,
    chunk_id: int
) -> Optional[Dict]:
    """Récupère un chunk spécifique."""
    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        scroll_filter = Filter(
            must=[
                FieldCondition(key="filepath", match=MatchValue(value=filepath)),
                FieldCondition(key="chunk_id", match=MatchValue(value=chunk_id))
            ]
        )

        points, _ = qdrant_client.scroll(
            collection_name=collection,
            scroll_filter=scroll_filter,
            limit=1,
            with_payload=True
        )

        if points:
            p = points[0].payload or {}
            return {
                "id": points[0].id,
                "score": 0.0,
                "text": p.get("text", ""),
                "filename": p.get("filename"),
                "filepath": p.get("filepath"),
                "chunk_id": p.get("chunk_id"),
                "model": p.get("model_label") or p.get("embedding_model")
            }
    except Exception as e:
        _rag_logger.warning(f"Erreur récupération chunk {chunk_id}: {e}")

    return None


def get_adjacent_chunks(
    collection: str,
    doc: Dict,
    chunks_before: int = 1,
    chunks_after: int = 1
) -> Dict[str, List[Dict]]:
    """Récupère les chunks adjacents."""
    result = {'before': [], 'current': doc, 'after': []}

    chunk_id = doc.get('chunk_id')
    filepath = doc.get('filepath')

    if chunk_id is None or filepath is None:
        return result

    try:
        chunk_num = int(chunk_id)
    except (ValueError, TypeError):
        return result

    for i in range(chunks_before, 0, -1):
        prev_chunk_id = chunk_num - i
        if prev_chunk_id >= 0:
            prev_doc = get_chunk_by_id(collection, filepath, prev_chunk_id)
            if prev_doc:
                result['before'].append(prev_doc)

    for i in range(1, chunks_after + 1):
        next_chunk_id = chunk_num + i
        next_doc = get_chunk_by_id(collection, filepath, next_chunk_id)
        if next_doc:
            result['after'].append(next_doc)

    return result


def expand_documents_with_context(
    collection: str,
    docs: List[Dict],
    chunks_before: int = 1,
    chunks_after: int = 1,
    merge_adjacent: bool = True
) -> List[Dict]:
    """Étend les documents avec leurs chunks adjacents."""
    if chunks_before == 0 and chunks_after == 0:
        return docs

    expanded_docs = []
    processed_chunks: Set[tuple] = set()

    for doc in docs:
        filepath = doc.get('filepath')
        chunk_id = doc.get('chunk_id')

        chunk_key = (filepath, chunk_id)
        if chunk_key in processed_chunks:
            continue
        processed_chunks.add(chunk_key)

        adjacent = get_adjacent_chunks(collection, doc, chunks_before, chunks_after)

        if merge_adjacent:
            all_chunks = adjacent['before'] + [adjacent['current']] + adjacent['after']
            merged_text = "\n\n".join(
                f"[Chunk {c.get('chunk_id', '?')}]\n{c.get('text', '')}"
                for c in all_chunks
            )
            expanded_doc = doc.copy()
            expanded_doc['text'] = merged_text
            expanded_doc['expanded'] = True
            expanded_doc['chunks_included'] = len(all_chunks)
            expanded_docs.append(expanded_doc)
        else:
            for chunk in adjacent['before']:
                chunk['is_context'] = True
                expanded_docs.append(chunk)
            doc['is_main'] = True
            expanded_docs.append(doc)
            for chunk in adjacent['after']:
                chunk['is_context'] = True
                expanded_docs.append(chunk)

    return expanded_docs


def rerank_docs_api(
    query: str,
    docs: List[Dict],
    openai_client: OpenAI,
    top_n: Optional[int] = None,
    min_rerank_score: Optional[float] = None,
    reranking_model: Optional[str] = None
) -> List[Dict]:
    """
    Rerank documents using API reranker.

    Args:
        query: Requête de recherche
        docs: Documents à reranker
        openai_client: Client OpenAI
        top_n: Nombre de documents à retourner
        min_rerank_score: Score minimum
        reranking_model: Modèle de reranking (utilise config si None)
    """
    config = get_rag_config()

    if top_n is None:
        top_n = config.reranking.top_n
    if min_rerank_score is None:
        min_rerank_score = config.reranking.min_rerank_score
    if reranking_model is None:
        reranking_model = config.models.reranking_model

    if not docs:
        return docs

    try:
        reranker = get_reranker_service(openai_client)
    except Exception as e:
        _rag_logger.warning(f"Reranker API indisponible : {e}")
        return docs[:top_n]

    # Préparer les documents
    max_chars = config.context.max_chars_per_doc
    documents = [d["text"][:max_chars] for d in docs]

    # Reranker via API
    try:
        results = reranker.rerank(
            query=query,
            documents=documents,
            model=reranking_model,
            top_n=top_n if top_n > 0 else None
        )

        # Associer les scores aux documents
        for result in results:
            doc_idx = result.get("index", 0)
            score = result.get("relevance_score", 0.0)
            if doc_idx < len(docs):
                docs[doc_idx]["rerank_score"] = float(score)

        # Filtrer et trier
        docs = [d for d in docs if d.get("rerank_score", 0.0) >= min_rerank_score]
        docs.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)

        return docs[:top_n]

    except Exception as e:
        _rag_logger.error(f"Erreur reranking API : {e}")
        return docs[:top_n]


def estimate_token_count(text: str) -> int:
    """Estime le nombre de tokens."""
    return len(text) // 4


def build_rag_system_message(
    query: str,
    collection: str,
    openai_client: OpenAI,
    top_k: Optional[int] = None,
    max_tokens: Optional[int] = None,
    embedding_model: Optional[str] = None,
    reranking_model: Optional[str] = None
) -> Optional[tuple]:
    """
    Build RAG system message with API embeddings and reranking.

    Args:
        query: Requête de recherche
        collection: Collection Qdrant
        openai_client: Client OpenAI
        top_k: Nombre de documents initiaux
        max_tokens: Budget maximum de tokens
        embedding_model: Modèle d'embedding (utilise config si None)
        reranking_model: Modèle de reranking (utilise config si None)
    """
    config = get_rag_config()

    if max_tokens is None:
        max_tokens = config.context.max_tokens

    # Retrieve documents using API embeddings
    docs = retrieve_relevant_docs(
        collection,
        query,
        openai_client,
        top_k=top_k,
        embedding_model=embedding_model
    )

    # Étendre avec contexte si configuré
    expand_config = config.retrieval.expand_context
    if expand_config.enabled and docs:
        if config.debug.show_rag_context:
            print(f"\n📚 Extension du contexte activée:")
            print(f"   - Chunks avant: {expand_config.chunks_before}")
            print(f"   - Chunks après: {expand_config.chunks_after}")

        docs = expand_documents_with_context(
            collection=collection,
            docs=docs,
            chunks_before=expand_config.chunks_before,
            chunks_after=expand_config.chunks_after,
            merge_adjacent=expand_config.merge_adjacent
        )

    # Rerank avec API
    docs = rerank_docs_api(query, docs, openai_client, reranking_model=reranking_model)

    if not docs:
        return None

    # Build context blocks
    context_blocks = []
    total_tokens = 0

    for d in docs:
        score = d.get("rerank_score") or d.get("score", 0.0)
        context_info = ""
        if d.get("expanded"):
            context_info = f" [+{d.get('chunks_included', 1)-1} chunks]"
        elif d.get("is_context"):
            context_info = " [contexte]"

        source_line = (
            f"{d.get('filename','?')} # "
            f"chunk {d.get('chunk_id', '?')}{context_info} # "
            f"score {round(score,3)}"
        )

        text = d.get('text', '')
        block = f"{source_line}\n{text}"

        block_tokens = estimate_token_count(block)
        if total_tokens + block_tokens > max_tokens:
            break

        context_blocks.append(block)
        total_tokens += block_tokens

    if not context_blocks:
        return None

    context = "\n\n".join(context_blocks)
    content = config.context.system_template.format(context=context)

    system_message = {"role": "system", "content": content}

    return system_message, docs
