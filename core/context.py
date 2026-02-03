"""Gestionnaire de contexte pour les documents."""
from typing import Optional, Any, List
import io
from pypdf import PdfReader

from utils.html import fetch_url_content


class ContextManager:
    """Gère l'extraction de contexte depuis différentes sources."""

    def extract_pdf_text(self, pdf_file: Any) -> str:
        """
        Extrait le texte d'un fichier PDF.

        Args:
            pdf_file: Fichier PDF (objet UploadedFile de Streamlit ou file-like)

        Returns:
            Texte extrait du PDF
        """
        try:
            # Créer un buffer bytes depuis le fichier
            if hasattr(pdf_file, 'read'):
                pdf_bytes = pdf_file.read()
                # Réinitialiser le pointeur si possible
                if hasattr(pdf_file, 'seek'):
                    pdf_file.seek(0)
            else:
                pdf_bytes = pdf_file

            # Créer un reader PDF
            pdf_reader = PdfReader(io.BytesIO(pdf_bytes))

            # Extraire le texte de toutes les pages
            text_parts = []
            for page_num, page in enumerate(pdf_reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- Page {page_num} ---\n{page_text}")

            full_text = "\n\n".join(text_parts)

            if not full_text.strip():
                return "[Le PDF ne contient pas de texte extractible]"

            return full_text

        except Exception as e:
            return f"[Erreur lors de l'extraction du PDF: {e}]"

    def extract_multiple_pdfs_text(self, pdf_files: List[Any]) -> str:
        """
        Extrait le texte de plusieurs fichiers PDF.

        Args:
            pdf_files: Liste de fichiers PDF

        Returns:
            Texte extrait de tous les PDFs, séparés par des marqueurs
        """
        if not pdf_files:
            return ""

        all_texts = []

        for idx, pdf_file in enumerate(pdf_files, 1):
            # Récupérer le nom du fichier si disponible
            filename = getattr(pdf_file, 'name', f"Document_{idx}")

            # Extraire le texte
            pdf_text = self.extract_pdf_text(pdf_file)

            # Ajouter avec un en-tête clair
            header = f"\n{'='*80}\n📄 DOCUMENT {idx}/{len(pdf_files)}: {filename}\n{'='*80}\n"
            all_texts.append(f"{header}{pdf_text}")

        return "\n\n".join(all_texts)

    def extract_url_content(self, url: str) -> str:
        """
        Extrait le contenu d'une URL.

        Args:
            url: URL à extraire

        Returns:
            Contenu texte de la page web
        """
        if not url:
            return ""

        try:
            content = fetch_url_content(
                url=url,
                timeout=8,
                max_chars=32_000,
                preserve_tables=True
            )

            if content.startswith("[Erreur"):
                return content

            return f"--- Contenu de {url} ---\n\n{content}"

        except Exception as e:
            return f"[Erreur lors de la récupération de l'URL: {e}]"

    def extract_text_file(self, text_file: Any) -> str:
        """
        Extrait le contenu d'un fichier texte.

        Args:
            text_file: Fichier texte (objet UploadedFile de Streamlit ou file-like)

        Returns:
            Contenu du fichier texte
        """
        try:
            if hasattr(text_file, 'read'):
                content = text_file.read()
                if hasattr(text_file, 'seek'):
                    text_file.seek(0)
            else:
                content = text_file

            # Décoder si bytes
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='ignore')

            return content

        except Exception as e:
            return f"[Erreur lors de la lecture du fichier: {e}]"
