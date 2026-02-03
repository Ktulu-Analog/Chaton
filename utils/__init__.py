"""Utilitaires pour l'application."""

from .latex import split_content, has_latex, strip_latex_delimiters, is_valid_latex
from .html import fetch_url_content, extract_table_as_text

__all__ = [
    # LaTeX
    'split_content',
    'has_latex',
    'strip_latex_delimiters',
    'is_valid_latex',
    # HTML
    'fetch_url_content',
    'extract_table_as_text',
]
