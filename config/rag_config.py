"""Configuration du système RAG depuis fichier YAML."""
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ExpandContextConfig:
    """Configuration de l'extension du contexte."""
    enabled: bool = True
    chunks_before: int = 1
    chunks_after: int = 1
    merge_adjacent: bool = True


@dataclass
class ModelConfig:
    """Configuration des modèles API."""
    embedding_model: str = "BAAI/bge-m3"  # Modèle d'embedding par défaut
    reranking_model: str = "BAAI/bge-reranker-v2-m3"  # Modèle de reranking par défaut
    embedding_dimensions: Optional[int] = None  # Dimensions des embeddings (optionnel)


@dataclass
class RetrievalConfig:
    """Configuration de la recherche sémantique."""
    top_k: int = 40
    min_score: float = 0.1
    batch_size: int = 32
    expand_context: ExpandContextConfig = field(default_factory=ExpandContextConfig)


@dataclass
class RerankingConfig:
    """Configuration du reranking."""
    top_n: int = 8
    min_rerank_score: float = 0.0
    batch_size: int = 32


@dataclass
class ChunkingConfig:
    """Configuration du découpage de texte."""
    chunk_size: int = 1000
    overlap: int = 200
    separators: List[str] = field(default_factory=lambda: [
        "\n\n", "\n", ". ", "! ", "? ", "; ", " "
    ])


@dataclass
class ContextConfig:
    """Configuration du contexte pour le LLM."""
    max_tokens: int = 8000
    max_chars_per_doc: int = 1800
    system_template: str = (
        "Les informations suivantes proviennent de documents internes.\n"
        "Utilise-les exclusivement pour répondre.\n\n{context}"
    )


@dataclass
class HighlightingConfig:
    """Configuration du surlignage."""
    min_word_length: int = 3
    highlight_sentences: bool = True
    highlight_color: str = "#fff3a0"


@dataclass
class PerformanceConfig:
    """Configuration des performances."""
    use_cache: bool = True
    cache_size: int = 256
    clear_gpu_memory: bool = True


@dataclass
class DebugConfig:
    """Configuration du débogage."""
    show_message_order: bool = False
    show_scores: bool = False
    show_rag_context: bool = False


@dataclass
class RAGConfig:
    """Configuration complète du système RAG."""

    models: ModelConfig = field(default_factory=ModelConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    reranking: RerankingConfig = field(default_factory=RerankingConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    highlighting: HighlightingConfig = field(default_factory=HighlightingConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    debug: DebugConfig = field(default_factory=DebugConfig)

    @classmethod
    def from_yaml(cls, yaml_path: str = "rag.yml") -> "RAGConfig":
        """Charge la configuration depuis un fichier YAML."""
        path = Path(yaml_path)

        if not path.exists():
            print(f"⚠️ Fichier {yaml_path} introuvable, utilisation des valeurs par défaut")
            return cls()

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data:
                print(f"⚠️ Fichier {yaml_path} vide, utilisation des valeurs par défaut")
                return cls()

            return cls(
                models=ModelConfig(**data.get('models', {})),
                retrieval=RetrievalConfig(
                    top_k=data.get('retrieval', {}).get('top_k', 40),
                    min_score=data.get('retrieval', {}).get('min_score', 0.1),
                    batch_size=data.get('retrieval', {}).get('batch_size', 32),
                    expand_context=ExpandContextConfig(
                        **data.get('retrieval', {}).get('expand_context', {})
                    )
                ),
                reranking=RerankingConfig(**data.get('reranking', {})),
                chunking=ChunkingConfig(**data.get('chunking', {})),
                context=ContextConfig(**data.get('context', {})),
                highlighting=HighlightingConfig(**data.get('highlighting', {})),
                performance=PerformanceConfig(**data.get('performance', {})),
                debug=DebugConfig(**data.get('debug', {}))
            )

        except Exception as e:
            print(f"❌ Erreur lors du chargement de {yaml_path}: {e}")
            print("Utilisation des valeurs par défaut")
            return cls()

    def to_dict(self) -> Dict[str, Any]:
        """Convertit la configuration en dictionnaire."""
        retrieval_dict = self.retrieval.__dict__.copy()
        retrieval_dict['expand_context'] = self.retrieval.expand_context.__dict__

        return {
            'models': self.models.__dict__,
            'retrieval': retrieval_dict,
            'reranking': self.reranking.__dict__,
            'chunking': self.chunking.__dict__,
            'context': self.context.__dict__,
            'highlighting': self.highlighting.__dict__,
            'performance': self.performance.__dict__,
            'debug': self.debug.__dict__
        }

    def save(self, yaml_path: str = "rag.yml"):
        """Sauvegarde la configuration dans un fichier YAML."""
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, allow_unicode=True)


# Instance globale de configuration
_rag_config: Optional[RAGConfig] = None


def get_rag_config(reload: bool = False) -> RAGConfig:
    """
    Récupère la configuration RAG (singleton).

    Args:
        reload: Force le rechargement depuis le fichier

    Returns:
        Instance de RAGConfig
    """
    global _rag_config
    if _rag_config is None or reload:
        _rag_config = RAGConfig.from_yaml()
    return _rag_config


def reload_rag_config():
    """Force le rechargement de la configuration."""
    return get_rag_config(reload=True)
