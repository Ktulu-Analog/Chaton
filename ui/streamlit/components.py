"""Composants d'entrée pour Streamlit."""
import streamlit as st
from typing import Optional, Any, List

from ui.base import UIInput


class StreamlitInput(UIInput):
    """Implémentation Streamlit des entrées utilisateur."""

    def __init__(self, sidebar: bool = False):
        """
        Args:
            sidebar: Si True, affiche les inputs dans la sidebar
        """
        self.container = st.sidebar if sidebar else st

    def get_text_input(self, label: str, **kwargs) -> Optional[str]:
        """Récupère une entrée texte."""
        value = self.container.text_input(label, **kwargs)
        return value if value else None

    def get_file_upload(self, label: str, file_types: List[str], **kwargs) -> Optional[Any]:
        """Récupère un fichier uploadé."""
        return self.container.file_uploader(label, type=file_types, **kwargs)

    def get_multiple_file_upload(self, label: str, file_types: List[str], **kwargs) -> List[Any]:
        """
        Récupère plusieurs fichiers uploadés.

        Args:
            label: Label du widget
            file_types: Types de fichiers acceptés
            **kwargs: Arguments supplémentaires pour file_uploader

        Returns:
            Liste de fichiers uploadés (peut être vide)
        """
        files = self.container.file_uploader(
            label,
            type=file_types,
            accept_multiple_files=True,
            **kwargs
        )
        return files if files else []

    def get_selectbox(self, label: str, options: List[str], **kwargs) -> str:
        """Affiche une liste de sélection."""
        return self.container.selectbox(label, options=options, **kwargs)

    def get_checkbox(self, label: str, **kwargs) -> bool:
        """Affiche une checkbox."""
        return self.container.checkbox(label, **kwargs)

    def get_number_input(self, label: str, **kwargs) -> int:
        """Récupère une entrée numérique."""
        return self.container.number_input(label, **kwargs)

    def get_chat_input(self, placeholder: str) -> Optional[str]:
        """Récupère l'entrée du chat."""
        value = st.chat_input(placeholder)
        return value if value else None
