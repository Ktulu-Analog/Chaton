"""Service de gestion des collections RAG (locales et distantes)."""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from openai import OpenAI
import os

from config.settings import ENABLE_REMOTE_COLLECTIONS
from services.qdrant import qdrant_available, qdrant_collections


@dataclass
class Collection:
    """Représente une collection RAG."""
    name: str
    source: str  # "local" ou "remote"
    id: Optional[str] = None
    visibility: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @property
    def display_name(self) -> str:
        """Nom d'affichage avec indicateur de source."""
        if self.source == "remote":
            return f"☁️ {self.name}"
        else:
            return f"💾 {self.name}"

    @property
    def is_hash_collection(self) -> bool:
        """Vérifie si c'est une collection de hashes (à cacher)."""
        return self.name.endswith("files_hashes")


class CollectionManager:
    """Gestionnaire unifié des collections locales et distantes."""

    def __init__(self, openai_client: OpenAI):
        """
        Initialise le gestionnaire de collections.

        Args:
            openai_client: Client OpenAI pour accéder aux collections distantes
        """
        self.openai_client = openai_client
        self._local_collections: List[Collection] = []
        self._remote_collections: List[Collection] = []

        # Charger les collections
        self._load_collections()

    def _load_collections(self):
        """Charge toutes les collections disponibles."""
        # Collections locales (Qdrant)
        if qdrant_available:
            self._local_collections = [
                Collection(name=name, source="local")
                for name in qdrant_collections
                if not name.endswith("files_hashes")  # Filtrer les collections de hashes
            ]

        # Collections distantes (Albert)
        if ENABLE_REMOTE_COLLECTIONS and self.openai_client:
            try:
                self._remote_collections = self._fetch_remote_collections()
            except Exception as e:
                print(f"⚠️ Erreur chargement collections distantes : {e}")
                self._remote_collections = []

    def _fetch_remote_collections(self) -> List[Collection]:
        """
        Récupère les collections distantes depuis l'API Albert.

        Returns:
            Liste des collections distantes (sans les collections de hashes)
        """
        collections = []
        offset = 0
        limit = 100

        # Récupérer l'API key depuis les variables d'environnement
        api_key = os.getenv("API-KEY")

        # Construire les headers avec l'API key
        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        while True:
            try:
                response = self.openai_client._client.request(
                    method="GET",
                    url="/collections",
                    params={"offset": offset, "limit": limit},
                    headers=headers,
                )

                payload = response.json()
                batch = payload.get("data", [])

                if not batch:
                    break

                for col in batch:
                    collection_name = col.get("name", "")

                    # Filtrer les collections de hashes
                    if collection_name.endswith("files_hashes"):
                        continue

                    collections.append(Collection(
                        name=collection_name,
                        source="remote",
                        id=col.get("id"),
                        visibility=col.get("visibility"),
                        created_at=col.get("created_at"),
                        updated_at=col.get("updated_at"),
                        metadata=col
                    ))

                offset += limit

            except Exception as e:
                print(f"⚠️ Erreur lors de la récupération des collections : {e}")
                break

        return collections

    def get_all_collections(self, include_hash_collections: bool = False) -> List[Collection]:
        """
        Retourne toutes les collections disponibles (locales + distantes).

        Args:
            include_hash_collections: Si True, inclut les collections de hashes

        Returns:
            Liste de toutes les collections
        """
        all_cols = self._local_collections + self._remote_collections

        if include_hash_collections:
            return all_cols

        # Par défaut, filtrer les collections de hashes
        return [col for col in all_cols if not col.is_hash_collection]

    def get_local_collections(self, include_hash_collections: bool = False) -> List[Collection]:
        """
        Retourne uniquement les collections locales.

        Args:
            include_hash_collections: Si True, inclut les collections de hashes
        """
        if include_hash_collections:
            return self._local_collections

        return [col for col in self._local_collections if not col.is_hash_collection]

    def get_remote_collections(self, include_hash_collections: bool = False) -> List[Collection]:
        """
        Retourne uniquement les collections distantes.

        Args:
            include_hash_collections: Si True, inclut les collections de hashes
        """
        if include_hash_collections:
            return self._remote_collections

        return [col for col in self._remote_collections if not col.is_hash_collection]

    def get_collection_by_name(self, name: str) -> Optional[Collection]:
        """
        Recherche une collection par son nom.

        Args:
            name: Nom de la collection (avec ou sans préfixe)

        Returns:
            Collection trouvée ou None
        """
        # Nettoyer le nom (enlever les emojis)
        clean_name = name.replace("☁️ ", "").replace("💾 ", "").strip()

        # Rechercher dans toutes les collections (y compris les hashes)
        for col in self.get_all_collections(include_hash_collections=True):
            if col.name == clean_name:
                return col
        return None

    def get_collection_names(self) -> List[str]:
        """
        Retourne les noms d'affichage de toutes les collections.

        Note: Exclut par défaut les collections de hashes.

        Returns:
            Liste des noms avec indicateurs de source
        """
        return [col.display_name for col in self.get_all_collections()]

    def reload(self):
        """Recharge toutes les collections."""
        self._load_collections()

    def is_remote_collection(self, collection_name: str) -> bool:
        """
        Vérifie si une collection est distante.

        Args:
            collection_name: Nom de la collection

        Returns:
            True si la collection est distante, False sinon
        """
        col = self.get_collection_by_name(collection_name)
        return col.source == "remote" if col else False

    def get_stats(self) -> Dict[str, int]:
        """
        Retourne des statistiques sur les collections.

        Returns:
            Dictionnaire avec le nombre de collections par source
        """
        return {
            "local": len(self._local_collections),
            "remote": len(self._remote_collections),
            "total": len(self.get_all_collections())
        }
