"""Service LLM avec support OpenAI uniquement."""
from openai import OpenAI
from typing import Dict, Optional, Callable
import yaml

from config.settings import BASE_URL, API_KEY


class LLMLogger:
    """Logger abstrait pour le service LLM."""

    def __init__(
        self,
        error_callback: Optional[Callable[[str], None]] = None,
        info_callback: Optional[Callable[[str], None]] = None
    ):
        self.error = error_callback or (lambda msg: print(f"ERROR: {msg}"))
        self.info = info_callback or (lambda msg: print(f"INFO: {msg}"))


# Logger global
_llm_logger = LLMLogger()


def set_llm_logger(logger: LLMLogger):
    """Configure le logger pour le service LLM."""
    global _llm_logger
    _llm_logger = logger


def get_llm_client() -> OpenAI:
    """
    Crée et retourne un client OpenAI.

    Returns:
        Instance du client OpenAI
    """
    _llm_logger.info(f"🌐 Client OpenAI initialisé - {BASE_URL}")
    return OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY
    )


def load_capability_rules(path: str = "model_capabilities.yaml") -> dict:
    """
    Charge les règles de détection des capacités depuis un fichier YAML.

    Args:
        path: Chemin vers le fichier de configuration

    Returns:
        Dictionnaire des règles de capacités
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)["capabilities"]
    except Exception as e:
        _llm_logger.error(f"Erreur chargement règles capacités : {e}")
        return {}


def list_available_models(client: OpenAI) -> Dict[str, Dict[str, bool]]:
    """
    Liste les modèles disponibles et détecte leurs capacités.

    Args:
        client: Client OpenAI

    Returns:
        Dictionnaire {model_id: {capability: bool}}
    """
    models = {}

    try:
        rules = load_capability_rules()
    except Exception as e:
        _llm_logger.error(f"Erreur chargement règles capacités : {e}")
        rules = {}

    try:
        response = client.models.list()
    except Exception as e:
        _llm_logger.error(f"Erreur récupération modèles : {e}")
        return models

    for m in response.data:
        mid = m.id.lower()
        caps = {}

        # Capacités explicites si présentes
        capabilities = getattr(m, "capabilities", None)
        if isinstance(capabilities, dict):
            for cap, value in capabilities.items():
                caps[cap.lower()] = bool(value)

        # Détection via règles YAML
        for cap, rule in rules.items():
            keywords = rule.get("keywords", [])
            if any(k in mid for k in keywords):
                caps[cap] = True

        if caps:
            models[m.id] = caps

    return models


def get_model_capabilities(client: OpenAI, model_id: str) -> Dict[str, bool]:
    """
    Récupère les capacités d'un modèle spécifique.

    Args:
        client: Client OpenAI
        model_id: ID du modèle

    Returns:
        Dictionnaire des capacités du modèle
    """
    all_models = list_available_models(client)
    return all_models.get(model_id, {})
