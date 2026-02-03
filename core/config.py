"""Configuration centrale de l'application."""
from typing import Dict, Optional
import yaml
from pathlib import Path

from services.llm import get_llm_client, list_available_models
from core.models import ModelInfo, ModelCapabilities


class AppConfig:
    """Configuration centrale de l'application."""

    def __init__(self, prompts_file: str = "prompts.yml"):
        """
        Initialise la configuration.

        Args:
            prompts_file: Chemin vers le fichier de prompts
        """
        # Client LLM (OpenAI)
        self.llm_client = get_llm_client()

        # Charger les prompts
        self.prompts = self._load_prompts(prompts_file)

        # Charger les modèles disponibles
        self.available_models = self._load_models()

    def _load_prompts(self, prompts_file: str) -> Dict[str, str]:
        """Charge les prompts depuis le fichier YAML."""
        path = Path(prompts_file)

        if not path.exists():
            return {"Défaut": "Tu es un assistant serviable."}

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                raw_prompts = data.get("prompts", {})

                # Extraire la valeur de 'prompt' pour chaque entrée
                processed_prompts = {}
                for name, content in raw_prompts.items():
                    if isinstance(content, dict) and 'prompt' in content:
                        # Extraire la valeur du prompt
                        processed_prompts[name] = content['prompt']
                    elif isinstance(content, str):
                        # Si c'est déjà un string, le garder tel quel
                        processed_prompts[name] = content
                    else:
                        # Par défaut, convertir en string
                        processed_prompts[name] = str(content)

                return processed_prompts

        except Exception as e:
            print(f"Erreur chargement prompts : {e}")
            return {"Défaut": "Tu es un assistant serviable."}

    def _load_models(self) -> Dict[str, ModelInfo]:
        """Charge les modèles disponibles depuis l'API."""
        models_dict = {}

        try:
            raw_models = list_available_models(self.llm_client)

            for model_id, caps in raw_models.items():
                capabilities = ModelCapabilities(
                    text_generation=caps.get("text-generation", False),
                    image_text_to_text=caps.get("image-text-to-text", False),
                    automatic_speech_recognition=caps.get("automatic-speech-recognition", False),
                    text_to_speech=caps.get("text-to-speech", False),
                    code=caps.get("code", False),
                    embedding=caps.get("embedding", False),
                    moderation=caps.get("moderation", False),
                )

                models_dict[model_id] = ModelInfo(
                    id=model_id,
                    capabilities=capabilities
                )

        except Exception as e:
            print(f"Erreur chargement modèles : {e}")

        return models_dict

    @property
    def available_prompts(self) -> list:
        """Retourne la liste des prompts disponibles."""
        return list(self.prompts.keys())

    def get_prompt(self, prompt_name: str) -> Optional[str]:
        """Récupère un prompt par son nom."""
        return self.prompts.get(prompt_name)

    def get_model_by_display_name(self, display_name: str) -> Optional[str]:
        """
        Récupère l'ID d'un modèle à partir de son nom d'affichage.

        Args:
            display_name: Nom d'affichage du modèle (avec emojis)

        Returns:
            ID du modèle ou None
        """
        for model_id, model_info in self.available_models.items():
            if model_info.display_name == display_name:
                return model_id
        return None

    def reload_prompts(self, prompts_file: str = "prompts.yml"):
        """Recharge les prompts depuis le fichier."""
        self.prompts = self._load_prompts(prompts_file)

    def reload_models(self):
        """Recharge la liste des modèles disponibles."""
        self.available_models = self._load_models()
