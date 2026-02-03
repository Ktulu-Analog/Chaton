"""Chargeur de styles DOCX depuis un fichier YAML."""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT


class DocxStyleConfig:
    """Configuration de styles DOCX chargée depuis YAML."""

    def __init__(self, config_path: str):
        """
        Initialise la configuration de styles.

        Args:
            config_path: Chemin vers le fichier YAML de configuration

        Raises:
            FileNotFoundError: Si le fichier de configuration n'existe pas
            yaml.YAMLError: Si le fichier YAML est invalide
        """
        self.config_path = Path(config_path)
        self.styles = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        Charge la configuration depuis le fichier YAML.

        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            yaml.YAMLError: Si le fichier YAML est invalide
        """
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Le fichier de configuration des styles est introuvable : {self.config_path}"
            )

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if not config:
            raise ValueError(f"Le fichier de configuration est vide : {self.config_path}")

        return config

    def get_metadata(self) -> Dict[str, str]:
        """
        Retourne les métadonnées du document.

        Raises:
            KeyError: Si la section 'metadata' est absente
        """
        return self.styles['metadata']

    def apply_normal_style(self, paragraph):
        """Applique le style normal à un paragraphe."""
        normal_style = self.styles['normal']
        self._apply_paragraph_style(paragraph, normal_style.get('paragraph', {}))

        if paragraph.runs:
            self._apply_font_style(paragraph.runs[0], normal_style.get('font', {}))

    def apply_heading_style(self, paragraph, level: int = 1):
        """
        Applique le style de titre à un paragraphe.

        Args:
            paragraph: Paragraphe à styliser
            level: Niveau du titre (1, 2, 3, etc.)
        """
        headings = self.styles['headings']
        heading_style = headings[str(level)]

        self._apply_paragraph_style(paragraph, heading_style.get('paragraph', {}))

        if paragraph.runs:
            self._apply_font_style(paragraph.runs[0], heading_style.get('font', {}))

    def apply_code_style(self, paragraph):
        """Applique le style de code à un paragraphe."""
        code_style = self.styles['code_block']
        self._apply_paragraph_style(paragraph, code_style.get('paragraph', {}))

        if paragraph.runs:
            self._apply_font_style(paragraph.runs[0], code_style.get('font', {}))

    def apply_list_bullet_style(self, paragraph):
        """Applique le style de liste à puces."""
        list_styles = self.styles['lists']
        bullet_style = list_styles['bullet']

        self._apply_paragraph_style(paragraph, bullet_style.get('paragraph', {}))

        if paragraph.runs:
            self._apply_font_style(paragraph.runs[0], bullet_style.get('font', {}))

    def apply_list_number_style(self, paragraph):
        """Applique le style de liste numérotée."""
        list_styles = self.styles['lists']
        number_style = list_styles['number']

        self._apply_paragraph_style(paragraph, number_style.get('paragraph', {}))

        if paragraph.runs:
            self._apply_font_style(paragraph.runs[0], number_style.get('font', {}))

    def get_table_style_name(self) -> str:
        """
        Retourne le nom du style de tableau.

        Raises:
            KeyError: Si la configuration du tableau est absente
        """
        tables = self.styles['tables']
        return tables['style_name']

    def _apply_paragraph_style(self, paragraph, style: Dict[str, Any]):
        """Applique les propriétés de style à un paragraphe."""
        fmt = paragraph.paragraph_format

        # Alignement
        if 'alignment' in style:
            alignment_str = style['alignment']
            alignment_map = {
                'LEFT': WD_PARAGRAPH_ALIGNMENT.LEFT,
                'CENTER': WD_PARAGRAPH_ALIGNMENT.CENTER,
                'RIGHT': WD_PARAGRAPH_ALIGNMENT.RIGHT,
                'JUSTIFY': WD_PARAGRAPH_ALIGNMENT.JUSTIFY,
            }
            fmt.alignment = alignment_map[alignment_str]

        # Indentations
        if 'left_indent' in style:
            fmt.left_indent = Inches(style['left_indent'])

        if 'right_indent' in style:
            fmt.right_indent = Inches(style['right_indent'])

        if 'first_line_indent' in style:
            fmt.first_line_indent = Inches(style['first_line_indent'])

        # Espacements
        if 'space_before' in style:
            fmt.space_before = Pt(style['space_before'])

        if 'space_after' in style:
            fmt.space_after = Pt(style['space_after'])

        if 'line_spacing' in style:
            fmt.line_spacing = style['line_spacing']

    def _apply_font_style(self, run, style: Dict[str, Any]):
        """Applique les propriétés de police à un run."""
        font = run.font

        if 'name' in style:
            font.name = style['name']

        if 'size' in style:
            font.size = Pt(style['size'])

        if 'bold' in style:
            font.bold = style['bold']

        if 'italic' in style:
            font.italic = style['italic']

        if 'underline' in style:
            font.underline = style['underline']

        if 'color' in style:
            color_hex = style['color']
            if color_hex.startswith('#'):
                color_hex = color_hex[1:]

            r = int(color_hex[0:2], 16)
            g = int(color_hex[2:4], 16)
            b = int(color_hex[4:6], 16)
            font.color.rgb = RGBColor(r, g, b)


# Instance globale de configuration
_style_config: Optional[DocxStyleConfig] = None


def load_style_config(config_path: str) -> DocxStyleConfig:
    """
    Charge ou recharge la configuration de styles.

    Args:
        config_path: Chemin vers le fichier YAML de configuration

    Returns:
        Instance de DocxStyleConfig

    Raises:
        FileNotFoundError: Si le fichier n'existe pas
    """
    global _style_config
    _style_config = DocxStyleConfig(config_path)
    return _style_config


def get_style_config() -> DocxStyleConfig:
    """
    Retourne la configuration de styles actuelle.

    Returns:
        Instance de DocxStyleConfig

    Raises:
        RuntimeError: Si aucune configuration n'a été chargée
    """
    global _style_config
    if _style_config is None:
        raise RuntimeError(
            "Aucune configuration de styles n'a été chargée. "
            "Appelez load_style_config() d'abord."
        )
    return _style_config


def reload_style_config():
    """
    Recharge la configuration de styles depuis le fichier.

    Raises:
        RuntimeError: Si aucune configuration n'a été chargée auparavant
    """
    global _style_config
    if _style_config is None:
        raise RuntimeError(
            "Aucune configuration de styles n'a été chargée. "
            "Appelez load_style_config() d'abord."
        )
    config_path = str(_style_config.config_path)
    _style_config = DocxStyleConfig(config_path)
