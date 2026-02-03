"""Classes de données pour l'application (UI-agnostic)."""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union


@dataclass
class Message:
    """Représente un message dans la conversation."""
    role: str  # "user", "assistant", "system"
    content: Union[str, List[Dict[str, Any]]]

    def to_dict(self) -> Dict[str, Any]:
        """Convertit le message en dictionnaire pour l'API."""
        return {
            "role": self.role,
            "content": self.content
        }


@dataclass
class ModelCapabilities:
    """Capacités d'un modèle LLM."""
    text_generation: bool = False
    image_text_to_text: bool = False
    automatic_speech_recognition: bool = False
    text_to_speech: bool = False
    code: bool = False
    embedding: bool = False
    moderation: bool = False

    def to_dict(self) -> Dict[str, bool]:
        return {
            "text-generation": self.text_generation,
            "image-text-to-text": self.image_text_to_text,
            "automatic-speech-recognition": self.automatic_speech_recognition,
            "text-to-speech": self.text_to_speech,
            "code": self.code,
            "embedding": self.embedding,
            "moderation": self.moderation,
        }


@dataclass
class ModelInfo:
    """Information sur un modèle disponible."""
    id: str
    capabilities: ModelCapabilities

    @property
    def display_name(self) -> str:
        """Nom d'affichage avec emojis."""
        emoji_map = {
            "text_generation": "📄",
            "image_text_to_text": "📊",
            "automatic_speech_recognition": "💬",
            "text_to_speech": "💬",
            "code": "💻",
            "embedding": "🧩",
            "moderation": "🛡️",
        }

        emojis = ""
        caps_dict = self.capabilities.__dict__
        for cap, present in caps_dict.items():
            if present and cap in emoji_map:
                emojis += emoji_map[cap]

        return f"{emojis} {self.id}"


@dataclass
class RAGDocument:
    """Document récupéré par le système RAG."""
    id: str
    text: str
    score: float
    filename: Optional[str] = None
    filepath: Optional[str] = None
    chunk_id: Optional[str] = None
    model: Optional[str] = None
    rerank_score: Optional[float] = None

    @property
    def best_score(self) -> float:
        """Retourne le meilleur score (rerank ou score original)."""
        return self.rerank_score if self.rerank_score is not None else self.score


@dataclass
class ChatContext:
    """Contexte additionnel pour la conversation."""
    pdf_text: Optional[str] = None
    url_content: Optional[str] = None
    system_prompt: Optional[str] = None
    rag_documents: List[RAGDocument] = field(default_factory=list)


@dataclass
class ChatRequest:
    """Requête de chat complète."""
    user_message: str
    uploaded_image: Optional[Any] = None
    context: ChatContext = field(default_factory=ChatContext)


@dataclass
class ChatResponse:
    """Réponse du système de chat."""
    content: str
    rag_sources: List[RAGDocument] = field(default_factory=list)
    error: Optional[str] = None
