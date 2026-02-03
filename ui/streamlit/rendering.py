##################################################################
# Rendu des éléments UI pour Streamlit
##################################################################
import streamlit as st
from typing import List, Optional
from core.models import Message, RAGDocument
from utils.latex import split_content, has_latex
from utils.docx_export import create_response_docx
from utils.xlsx_export import create_excel_export, detect_excel_content
from utils.pptx_export import create_powerpoint_export, detect_presentation_structure
from config.export_config import get_export_config
from datetime import datetime


class StreamlitRenderer:

    # Initialise le renderer avec la configuration des exports
    def __init__(self):
        self.export_config = get_export_config()

    def render_message(self, message: Message, question: str = None, model_name: str = None, message_index: int = 0):
        """
        Affiche un message de la conversation.

        Args:
            message: Message à afficher
            question: Question posée (pour l'export DOCX)
            model_name: Nom du modèle utilisé (pour l'export DOCX)
            message_index: Index du message dans la conversation (pour clés uniques)
        """
        with st.chat_message(message.role):
            if isinstance(message.content, str):
                self.render_content_with_latex(message.content)

                # Ajouter les boutons de téléchargement pour les réponses de l'assistant
                if message.role == "assistant" and question:
                    self._render_download_buttons(question, message.content, model_name, message_index)

            elif isinstance(message.content, list):
                # Contenu multimodal (texte + image)
                for item in message.content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            self.render_content_with_latex(item.get("text", ""))
                        elif item.get("type") == "image_url":
                            st.image(item.get("image_url", {}).get("url", ""))

    def _render_download_buttons(self, question: str, response: str, model_name: str = None, message_index: int = 0):
        """
        Affiche les boutons de téléchargement DOCX, XLSX et PPTX selon la configuration.

        Args:
            question: Question posée
            response: Réponse générée
            model_name: Nom du modèle utilisé
            message_index: Index du message pour rendre les clés uniques
        """
        # Créer les métadonnées
        metadata = {
            'date': datetime.now().strftime('%d/%m/%Y %H:%M'),
        }
        if model_name:
            metadata['model'] = model_name

        # Récupérer la configuration des exports
        enabled_exports = self.export_config.get_enabled_exports()

        # Détection du contenu (indépendante de la configuration)
        content_types = detect_excel_content(response)
        has_excel_content = any(content_types.values())

        presentation_structure = detect_presentation_structure(response)
        has_presentation_content = presentation_structure['has_slides'] or presentation_structure['has_bullets']

        # Déterminer quels boutons afficher selon la CONFIGURATION (pas le contenu)
        buttons_to_show = []

        # DOCX toujours présent
        buttons_to_show.append('docx')

        # Excel : seulement si activé dans la config
        if enabled_exports['excel']:
            buttons_to_show.append('excel')

        # PowerPoint : seulement si activé dans la config
        if enabled_exports['powerpoint']:
            buttons_to_show.append('powerpoint')

        # Créer les colonnes selon le nombre de boutons
        num_buttons = len(buttons_to_show)

        if num_buttons == 1:
            cols = [st.container()]
        elif num_buttons == 2:
            cols = st.columns(2)
        else:
            cols = st.columns(3)

        col_idx = 0

        # Timestamp et hash pour clés uniques
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        response_hash = hash(response[:100])

        # Bouton DOCX (toujours présent)
        if 'docx' in buttons_to_show:
            with cols[col_idx]:
                try:
                    docx_buffer = create_response_docx(question, response, metadata)
                    filename_docx = f"chaton_reponse_{timestamp}.docx"

                    st.download_button(
                        label="📥 DOCX",
                        data=docx_buffer.getvalue(),
                        file_name=filename_docx,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"download_docx_{timestamp}_{response_hash}_{message_index}",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erreur DOCX : {e}")

            col_idx += 1

        # Bouton XLSX (seulement si activé dans la config)
        if 'excel' in buttons_to_show:
            with cols[col_idx]:
                try:
                    xlsx_buffer = create_excel_export(question, response, metadata)
                    filename_xlsx = f"chaton_excel_{timestamp}.xlsx"

                    # Créer un label informatif si contenu Excel détecté
                    if has_excel_content:
                        excel_types = []
                        if content_types['has_formulas']:
                            excel_types.append("formules")
                        if content_types['has_vba']:
                            excel_types.append("VBA")
                        if content_types['has_tables']:
                            excel_types.append("tableaux")
                        label = f"📊 Excel"
                    else:
                        label = "📊 Excel"

                    st.download_button(
                        label=label,
                        data=xlsx_buffer.getvalue(),
                        file_name=filename_xlsx,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"download_xlsx_{timestamp}_{response_hash}_{message_index}",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erreur Excel : {e}")

            col_idx += 1

        # Bouton PPTX (seulement si activé dans la config)
        if 'powerpoint' in buttons_to_show:
            with cols[col_idx]:
                try:
                    pptx_buffer = create_powerpoint_export(question, response, metadata)
                    filename_pptx = f"chaton_presentation_{timestamp}.pptx"

                    label = "🎞️ PowerPoint"

                    st.download_button(
                        label=label,
                        data=pptx_buffer.getvalue(),
                        file_name=filename_pptx,
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        key=f"download_pptx_{timestamp}_{response_hash}_{message_index}",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Erreur PowerPoint : {e}")

    def _render_download_button(self, question: str, response: str, model_name: str = None, message_index: int = 0):
        """
        Méthode legacy pour compatibilité - redirige vers _render_download_buttons
        """
        self._render_download_buttons(question, response, model_name, message_index)

    def render_content_with_latex(self, content: str):
        """
        Affiche du contenu mixte texte/LaTeX.
        Utilise split_content pour séparer les blocs LaTeX du texte normal.
        """
        if not content:
            return

        # Séparer le contenu en blocs texte et LaTeX
        blocks = split_content(content)

        for block in blocks:
            if block["type"] == "latex":
                # Afficher le LaTeX avec st.latex
                try:
                    st.latex(block["content"])
                except Exception as e:
                    # En cas d'erreur LaTeX, afficher le texte brut
                    st.markdown(f"```\n{block['content']}\n```")
                    st.warning(f"Erreur LaTeX: {e}")
            else:
                # Afficher le texte normal avec Markdown
                # Nettoyer les balises HTML résiduelles
                text = block["content"]
                text = text.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
                st.markdown(text, unsafe_allow_html=False)

    def render_streaming_content(self, content: str):
        """
        Affiche du contenu en streaming avec support LaTeX.
        Détecte si le contenu contient du LaTeX et choisit le bon mode de rendu.
        """
        if not content:
            return

        # Nettoyer les balises HTML
        text = content.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')

        # Si le contenu contient du LaTeX complet (formules fermées),
        # utiliser le rendu avec LaTeX
        if has_latex(text):
            # Vérifier si les formules sont complètes (pas en cours de frappe)
            # Compter les délimiteurs
            dollar_count = text.count('$')
            double_dollar_count = text.count('$$')
            bracket_open = text.count(r'\[')
            bracket_close = text.count(r'\]')
            paren_open = text.count(r'\(')
            paren_close = text.count(r'\)')

            # Si les délimiteurs sont appariés, on peut rendre le LaTeX
            is_complete = (
                (dollar_count % 2 == 0 or double_dollar_count % 2 == 0) and
                bracket_open == bracket_close and
                paren_open == paren_close
            )

            if is_complete:
                self.render_content_with_latex(text)
                return

        # Sinon, utiliser Markdown simple pour la performance pendant le streaming
        st.markdown(text, unsafe_allow_html=False)

    def render_info(self, message: str):
        st.info(message)

    def render_warning(self, message: str):
        st.warning(message)

    def render_error(self, message: str):
        st.error(message)

    def render_success(self, message: str):
        st.success(message)

    def render_rag_sources(self, documents: List[RAGDocument]):
        if not documents:
            return

        with st.expander(f"📚 Sources utilisées pour générer la réponse ({len(documents)} documents)", expanded=False):
            for i, doc in enumerate(documents, 1):
                # Préparer les informations
                filename = doc.filename or "Document inconnu"
                chunk_id = doc.chunk_id if doc.chunk_id is not None else "?"
                score = doc.score or 0.0
                rerank_score = doc.rerank_score

                # En-tête du document
                header_parts = [f"**{i}. {filename}**"]

                #if chunk_id != "?":
                #    header_parts.append(f"Chunk {chunk_id}")

                if rerank_score is not None:
                    header_parts.append(f"Score: {rerank_score:.3f}")
                elif score > 0:
                    header_parts.append(f"Score: {score:.3f}")

                st.markdown(" • ".join(header_parts))

                # Afficher un extrait du texte
                if doc.text:
                    preview = doc.text[:300] + "..." if len(doc.text) > 300 else doc.text
                    # Nettoyer les balises HTML dans l'aperçu
                    preview = preview.replace('<br>', ' ').replace('<br/>', ' ')
                    st.markdown(f"> {preview}")

                # Séparateur
                if i < len(documents):
                    st.markdown("---")

    def render_code_block(self, code: str, language: str = "python"):
        st.code(code, language=language)

    def render_dataframe(self, data):
        st.dataframe(data)

    def render_json(self, data):
        st.json(data)

    def render_image(self, image_data, caption: Optional[str] = None):
        st.image(image_data, caption=caption)

    def render_divider(self):
        st.divider()

    def render_metric(self, label: str, value, delta: Optional[str] = None):
        st.metric(label, value, delta)

    def render_progress(self, progress: float, text: Optional[str] = None):
        st.progress(progress, text=text)
