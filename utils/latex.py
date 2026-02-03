"""Utilitaires pour le traitement du LaTeX dans le texte."""
import re
from typing import List, Dict


#======================================================================
# Patterns LaTeX
#======================================================================

LATEX_PATTERNS = {
    "markdown_math": re.compile(
        r"```math\s*(.*?)\s*```",
        re.DOTALL | re.IGNORECASE
    ),
    "environment": re.compile(
        r"\\begin\{([a-zA-Z*]+)\}.*?\\end\{\1\}",
        re.DOTALL
    ),
    "display_escaped": re.compile(
        r"\\\[.*?\\\]",  # \[...\] avec backslashes
        re.DOTALL
    ),
    "display_bracket": re.compile(
        r"\[\s*([^\[\]]+?)\s*\]",  # [ ... ] avec contenu (simplifié)
        re.DOTALL
    ),
    "display_dollar": re.compile(
        r"\$\$.*?\$\$",  # $$...$$
        re.DOTALL
    ),
    "inline": re.compile(
        r"\\\(.*?\\\)|(?<!\\)\$[^$\n]+?(?<!\\)\$"
    ),
}

LATEX_ORDER = [
    "markdown_math",
    "environment",
    "display_escaped",    # \[...\] en premier
    "display_bracket",    # [ ... ] avec LaTeX
    "display_dollar",     # $$...$$
    "inline",
]


#======================================================================
# Nettoyage délimiteurs
#======================================================================

def strip_latex_delimiters(expr: str) -> str:
    """
    Nettoie les délimiteurs de la chaîne LaTeX pour extraire l'expression mathématique brute.
    """
    s = expr.strip()

    # Nettoyage des balises de code mathématique
    if s.startswith("```"):
        return re.sub(r"^```math|```$", "", s, flags=re.IGNORECASE).strip()

    # Nettoyage des formules en mode affichage (entre $$...$$ ou \[...\])
    if s.startswith("$$") and s.endswith("$$"):
        return s[2:-2].strip()

    if s.startswith(r"\[") and s.endswith(r"\]"):
        return s[2:-2].strip()

    # Support pour [ ... ] sans backslashes (markdown LaTeX)
    if s.startswith("[") and s.endswith("]") and len(s) > 2:
        # Vérifier que c'est bien du LaTeX et pas un lien markdown
        inner = s[1:-1].strip()
        # Ne pas valider ici, juste extraire - la validation se fera après
        return inner

    # Nettoyage des formules en ligne (entre $...$ ou \(...\))
    if s.startswith(r"\(") and s.endswith(r"\)"):
        return s[2:-2].strip()

    if s.startswith("$") and s.endswith("$") and len(s) > 2:
        return s[1:-1].strip()

    # Environnements (ex : \begin{equation} ... \end{equation})
    if s.startswith(r"\begin"):
        return s.strip()

    return s


#======================================================================
# Validation sémantique
#======================================================================

LATEX_SEMANTIC_RE = re.compile(
    r"""
    (\\[a-zA-Z]+)       |  # Commandes LaTeX (ex : \frac, \sum)
    (\^|_)              |  # Puissances ou indices (ex : a^2, x_i)
    (\{|\})             |  # Accolades utilisées pour grouper des éléments (ex : \frac{a}{b})
    (=|<|>|\+|-|\*)     |  # Opérateurs mathématiques
    ([a-zA-Z]\s*=)         # Variables avec égalité (ex: E = mc^2)
    """,
    re.VERBOSE
)

# Patterns qui indiquent clairement que ce N'EST PAS du LaTeX
NON_LATEX_PATTERNS = [
    re.compile(r"^\[.*?\]\(.*?\)$"),  # Lien markdown [texte](url)
    re.compile(r"^\[[^\]]*https?://"),  # Début de lien markdown avec URL
    re.compile(r"^\[Cliquez|^Voir|^Plus d'info", re.IGNORECASE),  # Texte de lien typique
]

def is_valid_latex(expr: str, strict: bool = True) -> bool:
    """
    Vérifie si une expression est une expression LaTeX valide.
    Si strict est False, autorise des symboles mathématiques simples.
    """
    if not expr or len(expr) < 2:
        return False

    # Vérifier d'abord si c'est clairement PAS du LaTeX
    for pattern in NON_LATEX_PATTERNS:
        if pattern.search(expr):
            return False

    # Chercher des indicateurs LaTeX
    if LATEX_SEMANTIC_RE.search(expr):
        return True

    # En mode non-strict, accepter des expressions simples avec opérateurs
    if not strict:
        # Au moins un opérateur mathématique ou une lettre suivie de ^
        math_ops = any(c in expr for c in "+-*/^_=<>")
        has_super_sub = re.search(r'[a-zA-Z]\^|[a-zA-Z]_', expr)
        return math_ops or has_super_sub

    return False


#======================================================================
# Split principal
#======================================================================

def split_content_v2(
    text: str,
    strict: bool = False  # Changé à False par défaut pour être plus permissif
) -> List[Dict[str, str]]:
    """
    Sépare un texte mixte (texte et LaTeX) en blocs, où chaque bloc contient soit du texte soit du LaTeX.
    Retourne une liste de dictionnaires avec 'type' ("text" ou "latex") et 'content' (le contenu respectif).
    """

    parts = []
    cursor = 0
    matches = []

    # Recherche des correspondances LaTeX dans l'ordre des types définis
    for key in LATEX_ORDER:
        for m in LATEX_PATTERNS[key].finditer(text):
            matches.append((m.start(), m.end(), m.group(), key))

    # Trier les correspondances par position de début dans le texte
    matches.sort(key=lambda x: x[0])

    for start, end, raw, pattern_type in matches:
        if start < cursor:
            continue  # Ignorer les correspondances déjà traitées.

        if start > cursor:
            parts.append({
                "type": "text",
                "content": text[cursor:start]  # Ajouter le texte entre les blocs LaTeX.
            })

        # Nettoyage de l'expression LaTeX
        cleaned = strip_latex_delimiters(raw)

        # Validation : plus stricte pour les brackets simples [ ]
        is_bracket_pattern = pattern_type == "display_bracket"

        if is_bracket_pattern:
            # Pour [ ], vérifier strictement que c'est du LaTeX
            if is_valid_latex(cleaned, strict=False):
                parts.append({
                    "type": "latex",
                    "content": cleaned
                })
            else:
                # Si ce n'est pas du LaTeX, garder comme texte brut
                parts.append({
                    "type": "text",
                    "content": raw
                })
        else:
            # Pour les autres patterns ($$, \[, etc.), plus permissif
            if is_valid_latex(cleaned, strict=strict):
                parts.append({
                    "type": "latex",
                    "content": cleaned
                })
            else:
                parts.append({
                    "type": "text",
                    "content": raw
                })

        cursor = end  # Mettre à jour le curseur pour la prochaine itération.

    # Ajouter le reste du texte non traité
    if cursor < len(text):
        parts.append({
            "type": "text",
            "content": text[cursor:]
        })

    return parts


#======================================================================
# API publique
#======================================================================

def split_content(text: str) -> List[Dict[str, str]]:
    """
    Fonction publique pour séparer le texte en blocs LaTeX et texte normal.

    Args:
        text: Texte mixte contenant potentiellement du LaTeX

    Returns:
        Liste de dictionnaires avec 'type' ("text" ou "latex") et 'content'

    Example:
        >>> text = "Le théorème: $a^2 + b^2 = c^2$ est célèbre."
        >>> blocks = split_content(text)
        >>> # [{'type': 'text', 'content': 'Le théorème: '},
        >>> #  {'type': 'latex', 'content': 'a^2 + b^2 = c^2'},
        >>> #  {'type': 'text', 'content': ' est célèbre.'}]
    """
    return split_content_v2(text, strict=False)


def has_latex(text: str) -> bool:
    """
    Vérifie rapidement si un texte contient du LaTeX.

    Args:
        text: Texte à analyser

    Returns:
        True si du LaTeX est détecté, False sinon
    """
    if not text:
        return False

    # Recherche rapide de patterns LaTeX communs
    for key in LATEX_ORDER:
        if LATEX_PATTERNS[key].search(text):
            # Vérifier que c'est vraiment du LaTeX
            match = LATEX_PATTERNS[key].search(text)
            if match:
                cleaned = strip_latex_delimiters(match.group())
                if is_valid_latex(cleaned, strict=False):
                    return True

    return False
