"""Composants UI pour afficher les alertes de compatibilité des modèles."""
import streamlit as st
from typing import Optional, Dict


def render_model_compatibility_alert(
    detection: Dict,
    target_model: str,
    location: str = "sidebar"
) -> None:
    """
    Affiche une alerte de compatibilité de modèle.

    Args:
        detection: Résultat de la détection (depuis ModelDetector)
        target_model: Modèle cible configuré dans RAG
        location: 'sidebar' ou 'main' pour définir où afficher
    """
    if not detection:
        return

    container = st.sidebar if location == "sidebar" else st

    collection_model = detection.get('model_label')
    is_compatible = detection.get('is_compatible')
    dimension = detection.get('dimension')
    error = detection.get('error')

    # Erreur de détection
    if error:
        container.error(
            f"❌ **Erreur de détection**\n\n"
            f"{error}"
        )
        return

    # Modèle non détecté
    if not collection_model:
        container.warning(
            f"⚠️ **Modèle non détecté**\n\n"
            f"Impossible de détecter le modèle d'embedding "
            f"de cette collection.\n\n"
            f"**Causes possibles :**\n"
            f"• Collection vide\n"
            f"• Collection créée sans métadonnées de modèle\n"
            f"• Collection corrompue"
        )
        return

    # Modèle incompatible
    if not is_compatible:
        container.error(
            f"⚠️ **Incompatibilité de modèle détectée**\n\n"
            f"Cette collection a été indexée avec :\n"
            f"**`{collection_model}`**"
            f"{f' (dimension: {dimension})' if dimension else ''}\n\n"
            f"Ce modèle **n'est pas disponible** dans votre API.\n\n"
            f"**Actions recommandées :**\n"
            f"1. ✅ Réindexer la collection avec `{target_model}`\n"
            f"2. 🔄 Changer le modèle configuré dans `rag.yml`\n"
            f"3. 📚 Utiliser une autre collection"
        )

        # Afficher les modèles disponibles
        available_models = detection.get('available_models', [])
        if available_models:
            with container.expander("🔍 Modèles d'embedding disponibles dans l'API"):
                for model in available_models:
                    st.write(f"• `{model}`")

        return

    # Modèle différent mais compatible
    if collection_model != target_model:
        container.warning(
            f"ℹ️ **Modèle différent détecté**\n\n"
            f"**Collection indexée avec :** `{collection_model}`\n"
            f"**Configuration RAG actuelle :** `{target_model}`\n"
            f"{f'**Dimension :** {dimension}\n' if dimension else ''}\n"
            f"Les recherches utiliseront automatiquement "
            f"**`{collection_model}`** pour cette collection."
        )
        return

    # Modèle identique (optionnel : afficher une confirmation)
    if location == "sidebar":
        with container.expander("✅ Compatibilité vérifiée"):
            st.success(f"Modèle : `{collection_model}`")
            if dimension:
                st.info(f"Dimension : {dimension}")


def render_model_info_panel(
    detection: Dict,
    expanded: bool = False
) -> None:
    """
    Affiche un panneau d'informations détaillées sur le modèle.

    Args:
        detection: Résultat de la détection
        expanded: Si True, le panneau est déplié par défaut
    """
    if not detection:
        return

    with st.expander("📊 Informations sur le modèle d'embedding", expanded=expanded):
        collection_model = detection.get('model_label')
        dimension = detection.get('dimension')
        is_compatible = detection.get('is_compatible')
        error = detection.get('error')

        if error:
            st.error(f"Erreur : {error}")
            return

        if collection_model:
            col1, col2 = st.columns(2)

            with col1:
                st.metric("Modèle", collection_model)
                if dimension:
                    st.metric("Dimension", dimension)

            with col2:
                if is_compatible is not None:
                    status = "✅ Compatible" if is_compatible else "❌ Incompatible"
                    st.metric("Statut API", status)
        else:
            st.warning("Modèle non détecté dans la collection")


def render_quick_model_badge(
    detection: Dict,
    target_model: str
) -> None:
    """
    Affiche un badge rapide sur l'état de compatibilité.

    Args:
        detection: Résultat de la détection
        target_model: Modèle cible
    """
    if not detection:
        return

    collection_model = detection.get('model_label')
    is_compatible = detection.get('is_compatible')

    if not collection_model:
        st.caption("⚠️ Modèle non détecté")
    elif not is_compatible:
        st.caption(f"❌ Incompatible : `{collection_model}`")
    elif collection_model != target_model:
        st.caption(f"ℹ️ Utilise : `{collection_model}`")
    else:
        st.caption(f"✅ Compatible : `{collection_model}`")


def render_reindexing_help() -> None:
    """Affiche un guide de réindexation."""
    with st.expander("❓ Comment réindexer une collection ?"):
        st.markdown("""
        ### Réindexation avec l'utilitaire CLI

        ```bash
        # 1. Supprimer l'ancienne collection
        python qdrant_cli.py delete ma_collection

        # 2. Créer une nouvelle collection avec le bon modèle
        python qdrant_cli.py create ma_collection --model "BAAI/bge-m3"

        # 3. Réindexer vos documents
        python qdrant_cli.py index-folder ma_collection ./mes_docs
        ```

        ### Réindexation programmatique

        ```python
        from services.indexing import create_indexer
        from openai import OpenAI

        client = OpenAI(base_url=..., api_key=...)
        indexer = create_indexer(client)

        # Recréer la collection
        indexer.create_collection(
            "ma_collection",
            model="BAAI/bge-m3",
            recreate=True
        )

        # Réindexer
        indexer.index_documents(...)
        ```
        """)
