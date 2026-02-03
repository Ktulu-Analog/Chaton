"""Utilitaires pour la manipulation d'images."""
import base64
from typing import Union, BinaryIO
from io import BytesIO


def encode_image(image_file: Union[BinaryIO, bytes, BytesIO]) -> str:
    """
    Encode une image en base64 pour l'envoyer à l'API.

    Args:
        image_file: Fichier image (file upload, bytes, ou BytesIO)

    Returns:
        String base64 de l'image
    """
    # Si c'est déjà des bytes
    if isinstance(image_file, bytes):
        return base64.b64encode(image_file).decode('utf-8')

    # Si c'est un BytesIO ou un file-like object
    try:
        # Sauvegarder la position actuelle
        current_pos = image_file.tell() if hasattr(image_file, 'tell') else 0

        # Revenir au début du fichier
        if hasattr(image_file, 'seek'):
            image_file.seek(0)

        # Lire tout le contenu
        image_bytes = image_file.read()

        # Restaurer la position (optionnel, mais bonne pratique)
        if hasattr(image_file, 'seek'):
            image_file.seek(current_pos)

        # Encoder en base64
        return base64.b64encode(image_bytes).decode('utf-8')

    except Exception as e:
        raise ValueError(f"Impossible d'encoder l'image: {e}")


def validate_image_format(image_file: Union[BinaryIO, bytes, BytesIO]) -> bool:
    """
    Vérifie que le fichier est une image valide.

    Args:
        image_file: Fichier image à valider

    Returns:
        True si c'est une image valide, False sinon
    """
    try:
        from PIL import Image

        # Sauvegarder la position
        if hasattr(image_file, 'tell'):
            current_pos = image_file.tell()
        else:
            current_pos = 0

        # Revenir au début
        if hasattr(image_file, 'seek'):
            image_file.seek(0)

        # Essayer d'ouvrir l'image
        img = Image.open(image_file)
        img.verify()

        # Restaurer la position
        if hasattr(image_file, 'seek'):
            image_file.seek(current_pos)

        return True

    except Exception:
        return False
