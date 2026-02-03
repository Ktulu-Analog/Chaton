"""Interface abstraite pour les implémentations UI."""
from abc import ABC, abstractmethod
from typing import Optional, Any, List, Dict

from core.models import Message, RAGDocument


class UIRenderer(ABC):
    """Interface abstraite pour le rendu UI."""

    @abstractmethod
    def render_message(self, message: Message):
        """Affiche un message dans l'interface."""
        pass

    @abstractmethod
    def render_streaming_content(self, content: str):
        """Affiche du contenu en streaming."""
        pass

    @abstractmethod
    def render_error(self, error: str):
        """Affiche une erreur."""
        pass

    @abstractmethod
    def render_info(self, message: str):
        """Affiche une information."""
        pass

    @abstractmethod
    def render_warning(self, message: str):
        """Affiche un avertissement."""
        pass

    @abstractmethod
    def render_rag_sources(self, documents: List[RAGDocument]):
        """Affiche les sources RAG."""
        pass


class UIInput(ABC):
    """Interface abstraite pour les entrées utilisateur."""

    @abstractmethod
    def get_text_input(self, label: str, **kwargs) -> Optional[str]:
        """Récupère une entrée texte."""
        pass

    @abstractmethod
    def get_file_upload(self, label: str, file_types: List[str], **kwargs) -> Optional[Any]:
        """Récupère un fichier uploadé."""
        pass

    @abstractmethod
    def get_selectbox(self, label: str, options: List[str], **kwargs) -> str:
        """Affiche une liste de sélection."""
        pass

    @abstractmethod
    def get_checkbox(self, label: str, **kwargs) -> bool:
        """Affiche une checkbox."""
        pass

    @abstractmethod
    def get_number_input(self, label: str, **kwargs) -> int:
        """Récupère une entrée numérique."""
        pass

    @abstractmethod
    def get_chat_input(self, placeholder: str) -> Optional[str]:
        """Récupère l'entrée du chat."""
        pass


class UIState(ABC):
    """Interface abstraite pour la gestion de l'état UI."""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Récupère une valeur de l'état."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any):
        """Définit une valeur dans l'état."""
        pass

    @abstractmethod
    def clear(self, key: str):
        """Efface une valeur de l'état."""
        pass


class UIApplication(ABC):
    """Interface abstraite pour l'application UI."""

    def __init__(self):
        self.renderer: UIRenderer = None
        self.input: UIInput = None
        self.state: UIState = None

    @abstractmethod
    def setup_page(self, title: str, icon: str):
        """Configure la page principale."""
        pass

    @abstractmethod
    def render_sidebar(self):
        """Affiche la barre latérale."""
        pass

    @abstractmethod
    def render_main_content(self):
        """Affiche le contenu principal."""
        pass

    @abstractmethod
    def run(self):
        """Lance l'application."""
        pass
