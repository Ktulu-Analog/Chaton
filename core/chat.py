from typing import List, Dict, Any, Optional, Iterator
from openai import OpenAI

from .models import Message, ChatRequest, ChatResponse, ChatContext, RAGDocument
from services.rag import build_rag_system_message
from services.rag_remote import build_rag_context_from_remote
from utils.images import encode_image


class ChatManager:
    """Gère la conversation et les interactions avec le LLM."""

    def __init__(self, client: OpenAI):
        self.client = client
        self.conversation: List[Message] = []

    def add_message(self, message: Message):
        """Ajoute un message à la conversation."""
        self.conversation.append(message)

    def clear_conversation(self):
        """Efface toute la conversation."""
        self.conversation.clear()

    def reset_for_new_context(self):
        """
        Réinitialise la conversation en gardant uniquement les messages user/assistant.
        Supprime tous les messages système pour permettre l'ajout de nouveaux contextes.

        Utilisé lors de changement de modèle, de document, ou de paramètres.
        """
        # Garder uniquement les messages user et assistant
        self.conversation = [
            msg for msg in self.conversation
            if msg.role in ("user", "assistant")
        ]

    def should_reset_for_new_context(self, new_context: ChatContext) -> bool:
        """
        Détermine si la conversation doit être réinitialisée pour un nouveau contexte.

        Returns:
            True si un reset est nécessaire (changement de PDF, URL, ou prompt système)
        """
        # Si la conversation est vide, pas besoin de reset
        if not self.conversation:
            return False

        # Vérifier s'il y a déjà des messages système
        has_system_messages = any(msg.role == "system" for msg in self.conversation)

        # Si pas de messages système et nouveau contexte, on peut l'ajouter
        if not has_system_messages:
            return False

        # Si on a déjà des messages système et qu'on veut en ajouter de nouveaux,
        # il faut reset
        has_new_context = any([
            new_context.system_prompt,
            new_context.pdf_text,
            new_context.url_content
        ])

        return has_system_messages and has_new_context

    def get_conversation(self) -> List[Message]:
        """Retourne la conversation actuelle."""
        return self.conversation.copy()

    def get_messages_for_saving(self) -> List[Message]:
        """
        Retourne les messages à sauvegarder dans l'historique.
        Exclut les messages système RAG qui sont temporaires.
        """
        messages_to_save = [
            msg for msg in self.conversation
            if msg.role in ("user", "assistant") or
               (msg.role == "system" and not self._is_rag_message(msg))
        ]

        # Debug : afficher ce qui sera sauvegardé
        print(f"\n💾 Messages à sauvegarder: {len(messages_to_save)}")
        for i, msg in enumerate(messages_to_save, 1):
            role = msg.role
            content = msg.content if isinstance(msg.content, str) else "[multimodal]"
            preview = content[:80] + "..." if len(content) > 80 else content
            print(f"   {i}. [{role.upper()}] {preview}")

        return messages_to_save

    def _is_rag_message(self, message: Message) -> bool:
        """Détermine si un message système est un message RAG."""
        if message.role != "system":
            return False

        content = message.content
        if isinstance(content, str):
            # Les messages RAG contiennent ces patterns
            rag_patterns = [
                "Les informations suivantes proviennent de documents internes",
                "# chunk",  # Les messages RAG contiennent des références de chunks
                "# score",  # Les messages RAG contiennent des scores
            ]
            return any(pattern in content for pattern in rag_patterns)

        return False

    def build_user_message(
        self,
        text: str,
        image_data: Optional[Any] = None
    ) -> Message:
        """Construit un message utilisateur avec texte et optionnellement une image."""
        if image_data:
            img_b64 = encode_image(image_data)
            content = [
                {"type": "text", "text": text},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_b64}"
                    }
                }
            ]
        else:
            content = text

        return Message(role="user", content=content)

    def add_context(self, context: ChatContext):
        """
        Ajoute les contextes additionnels à la conversation.
        ORDRE IMPORTANT : system_prompt d'abord, puis les documents.

        NOTE: Les messages système doivent être ajoutés AVANT tout message user/assistant.
        Cette fonction ne doit être appelée qu'au début d'une conversation ou après clear_conversation().
        """
        # Vérifier qu'il n'y a pas déjà de messages user/assistant
        has_user_or_assistant = any(
            msg.role in ("user", "assistant")
            for msg in self.conversation
        )

        if has_user_or_assistant:
            # Si la conversation a déjà commencé, ne pas ajouter de messages système
            # Car OpenAI n'autorise pas system après user/assistant
            return

        # 1. D'abord le prompt système principal (rôle de prompts.yml)
        if context.system_prompt:
            self.add_message(Message(
                role="system",
                content=context.system_prompt
            ))

        # 2. Puis les documents contextuels (PDF, URL)
        if context.pdf_text:
            self.add_message(Message(
                role="system",
                content=f"Document PDF fourni :\n\n{context.pdf_text}"
            ))

        if context.url_content:
            self.add_message(Message(
                role="system",
                content=f"Contenu web fourni :\n\n{context.url_content}"
            ))

    def build_messages_for_api(
        self,
        rag_context: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Construit la liste de messages à envoyer à l'API.
        Insère le contexte RAG juste avant le dernier message utilisateur.

        IMPORTANT: Les messages système doivent TOUJOURS venir avant user/assistant.

        Args:
            rag_context: Message système RAG à insérer (optionnel)

        Returns:
            Liste de messages au format dict pour l'API
        """
        messages = []

        # Séparer les messages par rôle
        system_messages = [msg for msg in self.conversation if msg.role == "system"]
        user_assistant_messages = [msg for msg in self.conversation if msg.role in ("user", "assistant")]

        # 1. Ajouter d'abord TOUS les messages système permanents
        for msg in system_messages:
            messages.append(msg.to_dict())

        # 2. Insérer le contexte RAG (aussi un message système)
        #    AVANT tous les messages user/assistant
        if rag_context:
            messages.append(rag_context)

        # 3. Ajouter tous les messages user/assistant
        for msg in user_assistant_messages:
            messages.append(msg.to_dict())

        return messages

    def generate_response(
        self,
        model: str,
        rag_context: Optional[Dict] = None,
        stream: bool = True,
        debug: bool = False
    ) -> Iterator[str]:
        """
        Génère une réponse du LLM en streaming.

        Args:
            model: Nom du modèle à utiliser
            rag_context: Message système RAG à insérer (optionnel)
            stream: Active le streaming
            debug: Active le mode debug
        """
        messages = self.build_messages_for_api(rag_context)

        # Mode debug : afficher l'ordre des messages
        if debug:
            print("\n" + "="*60)
            print("DEBUG - ORDRE DES MESSAGES ENVOYÉS AU LLM:")
            print("="*60)
            for i, msg in enumerate(messages, 1):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if isinstance(content, str):
                    preview = content[:100] + "..." if len(content) > 100 else content
                else:
                    preview = "[contenu multimodal]"
                print(f"{i}. [{role.upper()}] {preview}")
            print("="*60 + "\n")

        response_stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=stream
        )

        for chunk in response_stream:
            if not chunk.choices:
                continue

            choice = chunk.choices[0]
            delta = getattr(choice, "delta", None)

            if not delta:
                continue

            content = getattr(delta, "content", None)
            if content:
                yield content

    def process_request(
        self,
        request: ChatRequest,
        model: str,
        use_rag: bool = False,
        rag_collection: Optional[str] = None,
        rag_top_k: int = 40,
        is_remote_collection: bool = False,
        debug: bool = False
    ) -> tuple[Iterator[str], List[RAGDocument]]:
        """
        Traite une requête complète et retourne le stream de réponse et les documents RAG.

        Args:
            request: Requête de chat
            model: Modèle LLM à utiliser
            use_rag: Active le RAG
            rag_collection: Nom de la collection RAG
            rag_top_k: Nombre de documents à récupérer
            is_remote_collection: True si la collection est distante
            debug: Active le mode debug
        """
        is_first_message = not any(
            msg.role in ("user", "assistant")
            for msg in self.conversation
        )

        if is_first_message:
            self.add_context(request.context)

        # Récupérer le contexte RAG
        rag_context = None
        rag_docs = []

        if use_rag and rag_collection:
            if debug:
                print(f"\n🔍 Tentative de récupération RAG:")
                print(f"   - Collection: {rag_collection}")
                print(f"   - Type: {'☁️ Distante (Albert)' if is_remote_collection else '💾 Locale (Qdrant)'}")
                print(f"   - Query: {request.user_message}")
                print(f"   - Top K: {rag_top_k}")

            # MODIFICATION : Choisir entre RAG local ou distant
            if is_remote_collection:
                # Utiliser le RAG distant (Albert API)
                result = build_rag_context_from_remote(
                    self.client,
                    rag_collection,
                    request.user_message,
                    rag_top_k
                )
            else:
                # MODIFICATION : Passer le client OpenAI au RAG local
                from services.rag import build_rag_system_message
                result = build_rag_system_message(
                    request.user_message,
                    rag_collection,
                    self.client,  # ← AJOUT DU CLIENT
                    rag_top_k
                )

            if debug:
                print(f"   - Résultat: {'✅ Documents trouvés' if result else '❌ Aucun document'}")

            if result:
                rag_msg, rag_docs_list = result
                rag_context = rag_msg

                if debug:
                    print(f"   - Nombre de documents: {len(rag_docs_list)}")

                # Convertir les dicts en RAGDocument
                rag_docs = [
                    RAGDocument(
                        id=d.get("id", ""),
                        text=d.get("text", ""),
                        score=d.get("score", 0.0),
                        filename=d.get("filename"),
                        filepath=d.get("filepath"),
                        chunk_id=d.get("chunk_id"),
                        model=d.get("model"),
                        rerank_score=d.get("rerank_score")
                    )
                    for d in rag_docs_list
                ]
            else:
                if debug:
                    source = "distant" if is_remote_collection else "local"
                    print(f"   ⚠️ build_rag (source: {source}) a retourné None")

        # Ajouter le message utilisateur
        user_msg = self.build_user_message(
            request.user_message,
            request.uploaded_image
        )
        self.add_message(user_msg)

        # Générer la réponse
        response_stream = self.generate_response(
            model,
            rag_context=rag_context,
            stream=True,
            debug=debug
        )

        return response_stream, rag_docs
