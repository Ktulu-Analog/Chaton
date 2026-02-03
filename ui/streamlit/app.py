##############################################################
# Application Streamlit principale
# 19/01/2026
##############################################################
import os
import streamlit as st
import random
from typing import Optional

from ui.base import UIApplication
from ui.streamlit.rendering import StreamlitRenderer
from ui.streamlit.components import StreamlitInput
from ui.streamlit.state import StreamlitState
from ui.streamlit.adapters import setup_streamlit_loggers

from core.config import AppConfig
from core.chat import ChatManager
from core.context import ContextManager
from core.models import ChatRequest, ChatContext, Message

from services.qdrant import qdrant_available, qdrant_collections
from services.collections import CollectionManager
from config.rag_config import get_rag_config, reload_rag_config
from config.export_config import get_export_config


class StreamlitChatApp(UIApplication):
    def __init__(self):
        super().__init__()

        # Configurer les loggers pour Streamlit
        setup_streamlit_loggers()

        # Configuration générale
        self.config = AppConfig()
        self.rag_config = get_rag_config()
        self.export_config = get_export_config()

        # Composants UI
        self.renderer = StreamlitRenderer()
        self.sidebar_input = StreamlitInput(sidebar=True)
        self.main_input = StreamlitInput(sidebar=False)
        self.state = StreamlitState()

        # Managers
        self.chat_manager = ChatManager(self.config.llm_client)
        self.context_manager = ContextManager()
        self.collection_manager = CollectionManager(self.config.llm_client)

        # Variables d'état
        self.selected_model = None
        self.selected_prompt = None
        self.uploaded_pdfs = []
        self.uploaded_image = None
        self.url_input = None
        self.use_rag = False
        self.selected_collection = None
        self.rag_top_k = None

    def setup_page(self, title: str = "Chaton 🐾", icon: str = "🐾"):
        st.set_page_config(
            page_title=title,
            page_icon=icon,
            layout="wide",
        )

        if os.path.exists("logo.png"):
            st.image("logo.png")

        st.markdown("**Vos infos ici et un logo au dessus si présence de logo.png**")
        st.title("Chaton 🐾 – le petit chat")

        st.write(random.choice([
            "Quel est le programme aujourd'hui ?",
            "Qu'est-ce qui vous intéresse aujourd'hui ?",
            "Toujours prêt à répondre."
        ]))

    def render_sidebar(self):
        st.sidebar.markdown("---")

        if st.sidebar.button("Nouvelle conversation", use_container_width=True, type="primary"):
            self.chat_manager.reset_for_new_context()
            self.state.set("conversation", [])
            self.state.set("context_key", "")
            st.rerun()

        self.selected_prompt = self.sidebar_input.get_selectbox(
            "Rôle",
            self.config.available_prompts
        )

        if not self.config.available_models:
            st.sidebar.error("❌ Aucun modèle LLM disponible")
            st.stop()

        model_labels = [
            model.display_name
            for model in self.config.available_models.values()
        ]

        selected_label = self.sidebar_input.get_selectbox(
            "**Modèles disponibles**",
            model_labels
        )

        self.selected_model = self.config.get_model_by_display_name(selected_label)

        # Afficher les capacités
        model_info = self.config.available_models[self.selected_model]
        caps = model_info.capabilities

        # Documents et médias
        st.sidebar.markdown("### 📂 Documents")

        # MULTI-UPLOAD DE PDFs
        self.uploaded_pdfs = self.sidebar_input.get_multiple_file_upload(
            "**Téléchargez un ou plusieurs PDFs**",
            ["pdf"]
        )

        # Afficher la liste des fichiers uploadés
        if self.uploaded_pdfs:
            st.sidebar.success(f"✅ {len(self.uploaded_pdfs)} PDF(s) chargé(s)")
            with st.sidebar.expander("📋 Fichiers chargés"):
                for idx, pdf in enumerate(self.uploaded_pdfs, 1):
                    file_size = pdf.size / 1024
                    st.write(f"{idx}. {pdf.name} ({file_size:.1f} KB)")

        if caps.image_text_to_text:
            self.uploaded_image = self.sidebar_input.get_file_upload(
                "**Téléchargez une image**",
                ["png", "jpg", "jpeg"]
            )

        self.url_input = self.sidebar_input.get_text_input("**Saisissez une adresse web**")

        st.sidebar.markdown("---")

        # Options RAG
        st.sidebar.markdown("### 🔎 Recherche RAG")
        self.use_rag = self.sidebar_input.get_checkbox("**Activer le RAG**", value=False)

        # Récupérer les statistiques des collections
        collection_stats = self.collection_manager.get_stats()

        if collection_stats['total'] > 0:

            # Sélection de la collection
            collection_names = self.collection_manager.get_collection_names()
            selected_collection_display = self.sidebar_input.get_selectbox(
                "**Sélectionnez une collection**",
                collection_names
            )

            # Récupérer la collection sélectionnée
            selected_collection = self.collection_manager.get_collection_by_name(
                selected_collection_display
            )

            if selected_collection:
                self.selected_collection = selected_collection.name


        else:
            st.sidebar.warning("❌ Aucune collection disponible")
            self.selected_collection = None

    def render_main_content(self):
        """Affiche le contenu principal."""
        main_container = st.container()
        footer_container = st.container()

        with main_container:
            self.state.initialize()

        # Créer une clé unique pour le contexte actuel
        pdf_signature = "_".join([pdf.name for pdf in self.uploaded_pdfs]) if self.uploaded_pdfs else "no_pdf"
        context_key = f"{self.selected_prompt}_{pdf_signature}_{bool(self.uploaded_image)}_{bool(self.url_input)}"

        # Vérifier si le contexte a changé
        previous_context = self.state.get("context_key", "")
        if context_key != previous_context:
            self.chat_manager.reset_for_new_context()
            self.state.set("context_key", context_key)
            self.state.set("conversation", [])

        # Reset si changement de prompt uniquement
        self.state.reset_conversation_if_needed(self.selected_prompt)

        # Afficher le profil actuel
        profile_info = f"Profil actuel : **{self.selected_prompt}**"
        if self.uploaded_pdfs:
            profile_info += f" | 📄 {len(self.uploaded_pdfs)} PDF(s) chargé(s)"
        self.renderer.render_info(profile_info)

        # Restaurer la conversation depuis l'état
        stored_conversation = self.state.get("conversation", [])
        self.chat_manager.conversation = [
            Message(**msg) if isinstance(msg, dict) else msg
            for msg in stored_conversation
        ]

        # Afficher l'historique
        current_question = None

        for msg_index, msg in enumerate(self.chat_manager.conversation):
            if msg.role == "system":
                continue

            if msg.role == "user":
                if isinstance(msg.content, str):
                    current_question = msg.content
                elif isinstance(msg.content, list):
                    for item in msg.content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            current_question = item.get("text", "")
                            break
                self.renderer.render_message(msg, message_index=msg_index)

            elif msg.role == "assistant":
                model_display_name = None
                if self.selected_model and self.selected_model in self.config.available_models:
                    model_display_name = self.config.available_models[self.selected_model].display_name

                self.renderer.render_message(
                    msg,
                    question=current_question,
                    model_name=model_display_name,
                    message_index=msg_index
                )
                current_question = None

        # Input utilisateur
        prompt = self.main_input.get_chat_input("Votre question…")

        if not prompt:
            st.stop()

        # Préparer le contexte avec TOUS les PDFs
        context = ChatContext()

        if self.uploaded_pdfs:
            context.pdf_text = self.context_manager.extract_multiple_pdfs_text(
                self.uploaded_pdfs
            )

        if self.url_input:
            context.url_content = self.context_manager.extract_url_content(self.url_input)

        context.system_prompt = self.config.get_prompt(self.selected_prompt)

        # Créer la requête
        request = ChatRequest(
            user_message=prompt,
            uploaded_image=self.uploaded_image,
            context=context
        )

        # Afficher le message utilisateur
        user_msg = self.chat_manager.build_user_message(
            request.user_message,
            request.uploaded_image
        )
        self.renderer.render_message(user_msg)

        # Traiter la requête
        try:
            with st.chat_message("assistant"):
                placeholder = st.empty()

                debug_mode = self.rag_config.debug.show_message_order

                # Vérifier si la collection est distante
                is_remote = self.collection_manager.is_remote_collection(
                    self.selected_collection
                ) if self.selected_collection else False

                response_stream, rag_docs = self.chat_manager.process_request(
                    request=request,
                    model=self.selected_model,
                    use_rag=self.use_rag,
                    rag_collection=self.selected_collection if self.use_rag else None,
                    rag_top_k=self.rag_top_k,
                    is_remote_collection=is_remote,
                    debug=debug_mode
                )

                # Accumuler la réponse
                full_response = ""
                for chunk in response_stream:
                    full_response += chunk
                    with placeholder.container():
                        self.renderer.render_streaming_content(full_response)

                # Affichage final avec LaTeX
                if full_response:
                    placeholder.empty()

                    self.chat_manager.add_message(Message(
                        role="assistant",
                        content=full_response
                    ))

                    new_message_index = len(self.chat_manager.conversation) - 1

                    with placeholder.container():
                        self.renderer.render_content_with_latex(full_response)

                        model_display_name = None
                        if self.selected_model and self.selected_model in self.config.available_models:
                            model_display_name = self.config.available_models[self.selected_model].display_name

                        self.renderer._render_download_button(
                            prompt,
                            full_response,
                            model_display_name,
                            message_index=new_message_index
                        )

            # Afficher les sources RAG
            if self.use_rag and rag_docs:
                self.renderer.render_rag_sources(rag_docs)

        except Exception as e:
            self.renderer.render_error(str(e))

        # Sauvegarder la conversation
        self.state.set("conversation", [
            msg.to_dict() for msg in self.chat_manager.conversation
        ])

        # Message d'avertissement
        st.markdown("---")
        st.caption("⚠️ Chaton est une IA et peut faire des erreurs. Veuillez vérifier les réponses.")

    def run(self):
        """Lance l'application."""
        self.setup_page()
        self.render_sidebar()
        self.render_main_content()


# Point d'entrée
if __name__ == "__main__":
    app = StreamlitChatApp()
    app.run()
