"""Gestion de l'état pour Streamlit."""
import streamlit as st
from typing import Any

from ui.base import UIState


class StreamlitState(UIState):
    """Implémentation Streamlit de la gestion d'état."""

    def get(self, key: str, default: Any = None) -> Any:
        """Récupère une valeur de l'état."""
        return st.session_state.get(key, default)

    def set(self, key: str, value: Any):
        """Définit une valeur dans l'état."""
        st.session_state[key] = value

    def clear(self, key: str):
        """Efface une valeur de l'état."""
        if key in st.session_state:
            del st.session_state[key]

    def initialize(self):
        """Initialise les clés nécessaires."""
        if "conversation" not in st.session_state:
            st.session_state.conversation = []

        if "last_prompt" not in st.session_state:
            st.session_state.last_prompt = None

    def reset_conversation_if_needed(self, current_prompt: str):
        """Réinitialise la conversation si le prompt a changé."""
        if st.session_state.get("last_prompt") != current_prompt:
            st.session_state.conversation = []
            st.session_state.last_prompt = current_prompt
