"""Configuration de l'application."""
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# ✅ CORRECTION : Utiliser BASE-URL et API-KEY avec tirets
BASE_URL = os.getenv("BASE-URL", "https://albert.api.etalab.gouv.fr")
API_KEY = os.getenv("API-KEY", "")

# Configuration Qdrant
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)

# Collections distantes
ENABLE_REMOTE_COLLECTIONS = os.getenv("ENABLE_REMOTE_COLLECTIONS", "true").lower() == "true"

# Validation
if not API_KEY:
    print("⚠️ WARNING: API-KEY n'est pas définie dans le fichier .env")
