"""Adaptateurs pour configurer les services avec Streamlit."""
import streamlit as st

from services.rag import RAGLogger, set_rag_logger
from services.llm import LLMLogger, set_llm_logger


def setup_streamlit_loggers():
    """
    Configure tous les loggers des services pour utiliser Streamlit.
    À appeler au démarrage de l'application Streamlit.
    """
    # Logger RAG
    rag_logger = RAGLogger(
        warning_callback=st.warning,
        error_callback=st.error
    )
    set_rag_logger(rag_logger)

    # Logger LLM
    llm_logger = LLMLogger(
        error_callback=st.error
    )
    set_llm_logger(llm_logger)


def setup_console_loggers():
    """
    Configure tous les loggers pour utiliser la console.
    Utile pour les tests ou l'utilisation en CLI.
    """
    # Logger RAG
    rag_logger = RAGLogger(
        warning_callback=lambda msg: print(f"⚠️  WARNING: {msg}"),
        error_callback=lambda msg: print(f"❌ ERROR: {msg}")
    )
    set_rag_logger(rag_logger)

    # Logger LLM
    llm_logger = LLMLogger(
        error_callback=lambda msg: print(f"❌ ERROR: {msg}")
    )
    set_llm_logger(llm_logger)
