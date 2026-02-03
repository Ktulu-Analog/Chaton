"""Service d'embeddings utilisant l'API OpenAI/Albert."""
from typing import List, Union
from openai import OpenAI
import numpy as np

from config.settings import BASE_URL, API_KEY


class APIEmbeddingService:
    """Service d'embeddings via API."""

    def __init__(self, client: OpenAI = None):
        """
        Initialise le service d'embeddings.

        Args:
            client: Client OpenAI (optionnel, en créera un si None)
        """
        self.client = client or OpenAI(
            base_url=BASE_URL,
            api_key=API_KEY
        )

    def encode(
        self,
        texts: Union[str, List[str]],
        model: str,
        dimensions: int = None
    ) -> Union[List[float], np.ndarray]:
        """
        Encode un ou plusieurs textes en embeddings.

        Args:
            texts: Texte(s) à encoder
            model: ID du modèle d'embedding
            dimensions: Nombre de dimensions (optionnel)

        Returns:
            Embedding(s) sous forme de liste ou array numpy
        """
        # Normaliser l'entrée en liste
        is_single = isinstance(texts, str)
        text_list = [texts] if is_single else texts

        # Préparer les paramètres
        params = {
            "input": text_list,
            "model": model,
            "encoding_format": "float"  # ✅ Force le format float pour Albert
        }

        if dimensions is not None:
            params["dimensions"] = dimensions

        # Appel API
        try:
            response = self.client.embeddings.create(**params)

            # Extraire les embeddings
            embeddings = [item.embedding for item in response.data]

            # Retourner selon le format d'entrée
            if is_single:
                return embeddings[0]
            else:
                return np.array(embeddings)

        except Exception as e:
            raise RuntimeError(f"Erreur lors de l'embedding API: {e}")

    def encode_query(self, query: str, model: str) -> List[float]:
        """
        Encode une requête en embedding.

        Args:
            query: Requête à encoder
            model: ID du modèle

        Returns:
            Embedding de la requête
        """
        return self.encode(query, model)

    def encode_batch(
        self,
        texts: List[str],
        model: str,
        batch_size: int = 32
    ) -> np.ndarray:
        """
        Encode un lot de textes par batches.

        Args:
            texts: Liste de textes
            model: ID du modèle
            batch_size: Taille des batches

        Returns:
            Array numpy des embeddings
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = self.encode(batch, model)
            all_embeddings.extend(embeddings if isinstance(embeddings, list) else embeddings.tolist())

        return np.array(all_embeddings)


# Instance globale (singleton)
_embedding_service = None


def get_embedding_service(client: OpenAI = None) -> APIEmbeddingService:
    """Récupère l'instance du service d'embeddings."""
    global _embedding_service

    if _embedding_service is None:
        _embedding_service = APIEmbeddingService(client)

    return _embedding_service
