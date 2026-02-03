import requests
from bs4 import BeautifulSoup
import html as html_lib
import re
from typing import Optional


def extract_table_as_text(table_tag) -> str:
    """
    Extrait un tableau HTML et le formate en texte structuré.
    Préserve la structure avec des séparateurs clairs.
    """
    # IMPORTANT: Traiter les <br> dans tout le tableau AVANT extraction
    for br in table_tag.find_all("br"):
        br.replace_with(" ")  # Remplacer par espace dans les cellules

    rows = []

    # Extraire les en-têtes si présents
    headers = []
    thead = table_tag.find('thead')
    if thead:
        for th in thead.find_all(['th', 'td']):
            text = th.get_text(strip=True)
            # Nettoyer les caractères d'échappement
            text = text.replace('\\n', ' ').replace('\\t', ' ')
            headers.append(text)

    # Si pas de thead, chercher les th dans tbody
    if not headers:
        first_row = table_tag.find('tr')
        if first_row:
            for th in first_row.find_all('th'):
                text = th.get_text(strip=True)
                text = text.replace('\\n', ' ').replace('\\t', ' ')
                headers.append(text)

    if headers:
        rows.append(" | ".join(headers))
        rows.append("-" * (len(" | ".join(headers))))

    # Extraire les lignes de données
    tbody = table_tag.find('tbody') or table_tag
    for tr in tbody.find_all('tr'):
        cells = []
        for td in tr.find_all(['td', 'th']):
            cell_text = td.get_text(strip=True)
            # Nettoyer tous les types de sauts de ligne
            cell_text = cell_text.replace('\n', ' ').replace('\\n', ' ').replace('\\t', ' ')
            # Nettoyer les espaces multiples
            cell_text = re.sub(r'\s+', ' ', cell_text).strip()
            if cell_text:  # N'ajouter que si non vide
                cells.append(cell_text)

        if cells:  # Éviter les lignes vides
            rows.append(" | ".join(cells))

    return "\n".join(rows)


#======================================================================
# Récupère le contenu d'une page web, nettoie le HTML pour ne garder
# que le texte principal et renvoie les premiers 'max_chars'
# caractères du texte nettoyé.
#======================================================================
def fetch_url_content(
    url: str,
    timeout: int = 8,
    max_chars: int = 32_000,
    preserve_tables: bool = True
) -> str:
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Traiter les tableaux AVANT de convertir en texte
        if preserve_tables:
            for table in soup.find_all('table'):
                table_text = extract_table_as_text(table)
                # Remplacer le tableau par son texte formaté
                table.replace_with(f"\n\n{table_text}\n\n")

        # Remplacer les <br> par des sauts de ligne AVANT de supprimer les tags
        for br in soup.find_all("br"):
            br.replace_with("\n")

        # Remplacer certains tags par des sauts de ligne pour préserver la structure
        for tag in soup.find_all(["p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6"]):
            # Ajouter un saut de ligne après le tag
            if tag.string:
                tag.string = tag.string + "\n"

        # Supprime les éléments HTML qui ne contiennent pas de texte utile pour le LLM
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
            tag.decompose()

        # Extraire le texte
        text = soup.get_text(separator="\n")

        # Décoder les entités HTML (comme &nbsp;, &lt;, etc.)
        text = html_lib.unescape(text)

        # Nettoyer les séquences d'échappement littérales (\n, \t, etc.)
        text = text.replace('\\n', '\n').replace('\\t', '  ').replace('\\r', '')

        # Nettoyer les espaces multiples sur une même ligne
        lines = []
        for line in text.splitlines():
            # Supprimer les espaces multiples mais garder les indentations
            cleaned_line = re.sub(r'  +', ' ', line.strip())
            if cleaned_line:
                lines.append(cleaned_line)

        cleaned = "\n".join(lines)

        # Réduire les sauts de ligne multiples à maximum 2
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

        return cleaned[:max_chars]

    except Exception as e:
        return f"[Erreur lors de la récupération de l'URL] {e}"
