"""Gestionnaire de configuration pour les options d'export"""
import configparser
import os
from typing import Dict


class ExportConfig:
    """Gère la configuration des options d'export"""

    def __init__(self, config_path: str = "config/exports.ini"):
        """
        Initialise la configuration.

        Args:
            config_path: Chemin vers le fichier de configuration
        """
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self._load_config()

    def _load_config(self):
        """Charge le fichier de configuration"""
        if os.path.exists(self.config_path):
            self.config.read(self.config_path, encoding='utf-8')
        else:
            # Créer une configuration par défaut si le fichier n'existe pas
            self._create_default_config()

    def _create_default_config(self):
        """Crée et sauvegarde la configuration par défaut"""
        # Créer le répertoire config s'il n'existe pas
        config_dir = os.path.dirname(self.config_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)

        self.config['EXPORTS'] = {
            'Excel': 'oui',
            'PowerPoint': 'oui'
        }

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.config.write(f)
        except Exception as e:
            print(f"Erreur lors de la création du fichier de configuration : {e}")

    def _parse_bool(self, value: str) -> bool:
        """
        Convertit une valeur de configuration en booléen.

        Args:
            value: Valeur à convertir (oui/non, true/false, 1/0)

        Returns:
            True si activé, False sinon
        """
        if isinstance(value, bool):
            return value

        value_lower = str(value).lower().strip()
        return value_lower in ('oui', 'yes', 'true', '1', 'on', 'actif', 'activé')

    def is_excel_enabled(self) -> bool:
        """
        Vérifie si l'export Excel est activé.

        Returns:
            True si activé, False sinon
        """
        try:
            value = self.config.get('EXPORTS', 'Excel', fallback='oui')
            return self._parse_bool(value)
        except Exception:
            return True  # Par défaut, activé

    def is_powerpoint_enabled(self) -> bool:
        """
        Vérifie si l'export PowerPoint est activé.

        Returns:
            True si activé, False sinon
        """
        try:
            value = self.config.get('EXPORTS', 'PowerPoint', fallback='oui')
            return self._parse_bool(value)
        except Exception:
            return True  # Par défaut, activé

    def get_enabled_exports(self) -> Dict[str, bool]:
        """
        Retourne l'état de tous les exports.

        Returns:
            Dictionnaire avec l'état de chaque export
        """
        return {
            'excel': self.is_excel_enabled(),
            'powerpoint': self.is_powerpoint_enabled()
        }

    def reload(self):
        """Recharge la configuration depuis le fichier"""
        self._load_config()


# Instance globale
_config_instance = None


def get_export_config() -> ExportConfig:
    """
    Retourne l'instance singleton de la configuration.

    Returns:
        Instance de ExportConfig
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = ExportConfig()
    return _config_instance
