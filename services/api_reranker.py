"""Service de reranking utilisant l'API OpenAI/Albert."""
from typing import List, Dict, Tuple
from openai import OpenAI
import requests

from config.settings import BASE_URL, API_KEY

# Debug : afficher la config au démarrage
print(f"🔧 Config Reranker API:")
print(f"   BASE_URL: {BASE_URL}")
print(f"   API_KEY: {'✅ définie' if API_KEY else '❌ manquante'}")


class APIRerankerService:
    """Service de reranking via API."""

    def __init__(self, client: OpenAI = None):
        """
        Initialise le service de reranking.

        Args:
            client: Client OpenAI (optionnel)
        """
        self.client = client or OpenAI(
            base_url=BASE_URL,
            api_key=API_KEY
        )
        self.api_key = API_KEY
        # ✅ Construire l'URL complète pour le reranking
        # BASE_URL = https://albert.api.etalab.gouv.fr/v1/
        self.rerank_url = BASE_URL.rstrip('/') + '/rerank'

    def rerank(
        self,
        query: str,
        documents: List[str],
        model: str,
        top_n: int = None
    ) -> List[Dict]:
        """
        Rerank des documents selon leur pertinence par rapport à la requête.

        Args:
            query: Requête de recherche
            documents: Liste de textes à reranker
            model: ID du modèle de reranking
            top_n: Nombre de résultats à retourner (0 ou None = tous)

        Returns:
            Liste de dicts avec index, score et relevance_score
        """
        if not documents:
            return []

        # ✅ Préparer les paramètres selon la spec Albert
        params = {
            "query": query,
            "documents": documents,
            "model": model
        }

        # Albert accepte top_n = 0 pour "tous les résultats"
        if top_n is not None:
            params["top_n"] = top_n
        else:
            params["top_n"] = 0  # Retourner tous les résultats par défaut

        # Headers avec authentification
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            # Debug temporaire
            print(f"\n🔍 DEBUG Rerank:")
            print(f"   URL complète: {self.rerank_url}")
            print(f"   Model: {model}")
            print(f"   Query: {query[:50]}...")
            print(f"   Documents: {len(documents)}")

            # ✅ Utiliser requests directement pour plus de contrôle
            response = requests.post(
                self.rerank_url,
                json=params,
                headers=headers,
                timeout=30
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"Erreur API rerank (status {response.status_code}): "
                    f"{response.text}"
                )

            data = response.json()

            # ✅ Albert retourne 'results'
            results = data.get("results", data.get("data", []))

            # ✅ Normaliser le format de sortie
            normalized_results = []
            for r in results:
                normalized_results.append({
                    "index": r.get("index", 0),
                    "relevance_score": r.get("relevance_score", r.get("score", 0.0)),
                    "document": r.get("document", "")
                })

            return normalized_results

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Erreur de connexion lors du reranking API: {e}")
        except Exception as e:
            raise RuntimeError(f"Erreur lors du reranking API: {e}")

    def predict(
        self,
        pairs: List[Tuple[str, str]],
        model: str,
        convert_to_numpy: bool = False
    ) -> List[float]:
        """
        Prédit les scores de pertinence pour des paires (query, document).
        Compatible avec l'interface du CrossEncoder local.

        Args:
            pairs: Liste de tuples (query, document)
            model: ID du modèle
            convert_to_numpy: Ignoré (pour compatibilité)

        Returns:
            Liste de scores de pertinence
        """
        if not pairs:
            return []

        # Grouper par query (optimisation si même query)
        query_groups = {}
        for i, (query, doc) in enumerate(pairs):
            if query not in query_groups:
                query_groups[query] = []
            query_groups[query].append((i, doc))

        # Préparer les résultats
        scores = [0.0] * len(pairs)

        # Reranker par groupe de query
        for query, items in query_groups.items():
            indices = [i for i, _ in items]
            documents = [doc for _, doc in items]

            try:
                results = self.rerank(query, documents, model, top_n=0)

                # Mapper les scores aux indices originaux
                for result in results:
                    doc_idx = result.get("index", 0)
                    if doc_idx < len(indices):
                        original_idx = indices[doc_idx]
                        score = result.get("relevance_score", 0.0)
                        scores[original_idx] = score

            except Exception as e:
                print(f"⚠️ Erreur reranking pour query '{query[:50]}...': {e}")
                continue

        return scores


# Instance globale (singleton)
_reranker_service = None


def get_reranker_service(client: OpenAI = None) -> APIRerankerService:
    """Récupère l'instance du service de reranking."""
    global _reranker_service

    if _reranker_service is None:
        _reranker_service = APIRerankerService(client)

    return _reranker_service
