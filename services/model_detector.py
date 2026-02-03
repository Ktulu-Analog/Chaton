"""Service de détection des modèles d'embedding dans les collections."""
from typing import Optional, Dict, List
from openai import OpenAI
from services.qdrant import qdrant_client, qdrant_available
from config.settings import BASE_URL, API_KEY


class ModelDetector:
    """Détecte les modèles d'embedding utilisés dans les collections."""

    def __init__(self, openai_client: Optional[OpenAI] = None):
        """
        Initialise le détecteur.

        Args:
            openai_client: Client OpenAI pour récupérer les modèles disponibles
        """
        self.openai_client = openai_client or OpenAI(
            base_url=BASE_URL,
            api_key=API_KEY
        )
        self._available_models_cache = None

    def get_available_embedding_models(self) -> List[str]:
        """
        Récupère la liste des modèles d'embedding disponibles dans l'API.

        Returns:
            Liste des IDs de modèles d'embedding disponibles
        """
        if self._available_models_cache is not None:
            return self._available_models_cache

        try:
            # Récupérer tous les modèles
            models = self.openai_client.models.list()

            # Filtrer les modèles d'embedding
            embedding_models = []
            for model in models.data:
                # Vérifier si le modèle supporte l'embedding
                # En général, les modèles d'embedding ont "embed" dans leur nom
                # ou sont explicitement listés dans les capabilities
                model_id = model.id.lower()

                # Vérifier les capabilities si disponibles
                capabilities = getattr(model, 'capabilities', {})
                if isinstance(capabilities, dict):
                    if capabilities.get('embeddings') or capabilities.get('embedding'):
                        embedding_models.append(model.id)
                        continue

                # Sinon, détecter par le nom
                if any(keyword in model_id for keyword in ['embed', 'bge', 'e5', 'gte']):
                    embedding_models.append(model.id)

            self._available_models_cache = embedding_models
            return embedding_models

        except Exception as e:
            print(f"⚠️ Erreur lors de la récupération des modèles : {e}")
            return []

    def detect_collection_model(self, collection_name: str) -> Optional[Dict]:
        """
        Détecte le modèle d'embedding utilisé pour une collection locale.

        Args:
            collection_name: Nom de la collection

        Returns:
            Dict avec 'model_label', 'dimension', 'is_compatible'
            ou None si impossible à détecter
        """
        if not qdrant_available:
            return None

        try:
            # Récupérer un point de la collection pour voir le modèle
            points, _ = qdrant_client.scroll(
                collection_name=collection_name,
                limit=1,
                with_payload=True
            )

            if not points:
                return {
                    'model_label': None,
                    'dimension': None,
                    'is_compatible': None,
                    'error': 'Collection vide'
                }

            # Extraire le modèle du payload
            payload = points[0].payload or {}
            model_label = (
                payload.get("model_label") or
                payload.get("embedding_model") or
                payload.get("model")
            )

            # Récupérer la dimension de la collection
            collection_info = qdrant_client.get_collection(collection_name)
            dimension = collection_info.config.params.vectors.size

            # Vérifier si le modèle est compatible
            available_models = self.get_available_embedding_models()
            is_compatible = model_label in available_models if model_label else None

            return {
                'model_label': model_label,
                'dimension': dimension,
                'is_compatible': is_compatible,
                'available_models': available_models
            }

        except Exception as e:
            return {
                'model_label': None,
                'dimension': None,
                'is_compatible': None,
                'error': str(e)
            }

    def check_model_compatibility(
        self,
        collection_name: str,
        target_model: str
    ) -> Dict:
        """
        Vérifie la compatibilité entre le modèle de la collection et un modèle cible.

        Args:
            collection_name: Nom de la collection
            target_model: Modèle d'embedding cible à utiliser

        Returns:
            Dict avec le résultat de la vérification
        """
        detection = self.detect_collection_model(collection_name)

        if not detection or detection.get('error'):
            return {
                'compatible': False,
                'reason': detection.get('error', 'Impossible de détecter le modèle'),
                'recommendation': 'Vérifiez que la collection existe et contient des données'
            }

        collection_model = detection.get('model_label')

        # Si pas de modèle détecté
        if not collection_model:
            return {
                'compatible': False,
                'reason': 'Modèle d\'embedding non détecté dans la collection',
                'recommendation': 'Cette collection doit être réindexée avec un modèle compatible'
            }

        # Si le modèle est le même
        if collection_model == target_model:
            return {
                'compatible': True,
                'reason': 'Le modèle correspond exactement'
            }

        # Si le modèle de la collection n'est pas dans l'API
        if not detection.get('is_compatible'):
            return {
                'compatible': False,
                'reason': f'Le modèle "{collection_model}" n\'est pas disponible dans l\'API',
                'recommendation': f'Réindexez la collection avec "{target_model}" ou un autre modèle disponible',
                'collection_model': collection_model,
                'available_models': detection.get('available_models', [])
            }

        # Si les modèles sont différents mais tous deux disponibles
        return {
            'compatible': False,
            'reason': f'La collection utilise "{collection_model}" mais vous tentez d\'utiliser "{target_model}"',
            'recommendation': f'Utilisez "{collection_model}" ou réindexez la collection avec "{target_model}"',
            'collection_model': collection_model,
            'target_model': target_model
        }

    def get_recommended_model(self, collection_name: str) -> Optional[str]:
        """
        Retourne le modèle recommandé pour une collection.

        Args:
            collection_name: Nom de la collection

        Returns:
            ID du modèle recommandé ou None
        """
        detection = self.detect_collection_model(collection_name)

        if not detection or detection.get('error'):
            return None

        # Si le modèle de la collection est compatible, le recommander
        if detection.get('is_compatible'):
            return detection.get('model_label')

        # Sinon, retourner None (il faut réindexer)
        return None


def create_model_detector(openai_client: Optional[OpenAI] = None) -> ModelDetector:
    """
    Factory pour créer un détecteur de modèles.

    Args:
        openai_client: Client OpenAI (optionnel)

    Returns:
        Instance de ModelDetector
    """
    return ModelDetector(openai_client)
