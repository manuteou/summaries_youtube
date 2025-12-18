"""
utils.py - Utility functions for the YouTube Summarizer

Ce module contient des fonctions utilitaires réutilisables
avec des annotations de type complètes.
"""

import re
import os
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone


# =============================================================================
# TIME FORMATTING
# =============================================================================

# Intervalles de temps en secondes pour le formatage
TIME_INTERVALS = (
    ('ans', 31536000),       # 60 * 60 * 24 * 365
    ('mois', 2592000),       # 60 * 60 * 24 * 30
    ('semaines', 604800),    # 60 * 60 * 24 * 7
    ('jours', 86400),        # 60 * 60 * 24
    ('heures', 3600),        # 60 * 60
    ('minutes', 60),
    ('secondes', 1),
)


def time_since(date_obj: Optional[datetime]) -> str:
    """
    Retourne une chaîne indiquant le temps écoulé depuis la date donnée.
    
    Args:
        date_obj: Date à comparer (peut être None)
        
    Returns:
        Chaîne formatée (ex: "il y a 2 ans", "il y a 3 mois")
        
    Examples:
        >>> time_since(datetime.now() - timedelta(days=5))
        'il y a 5 jours'
    """
    if not date_obj:
        return "Date inconnue"
    
    # S'assurer que la date est timezone-aware
    if date_obj.tzinfo is None:
        date_obj = date_obj.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    diff = now - date_obj
    seconds = diff.total_seconds()
    
    for name, count in TIME_INTERVALS:
        value = seconds // count
        if value >= 1:
            return f"il y a {int(value)} {name}"
    
    return "à l'instant"


# =============================================================================
# STRING UTILITIES
# =============================================================================

def slugify(value: str) -> str:
    """
    Convertit une chaîne en slug URL-safe.
    
    Args:
        value: Chaîne à convertir
        
    Returns:
        Slug en minuscules avec underscores
        
    Examples:
        >>> slugify("Hello World!")
        'hello_world'
    """
    value = value.lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"\s+", "_", value)
    return value.strip("_")


def format_views(views: Optional[int]) -> str:
    """
    Formate un nombre de vues en chaîne lisible.
    
    Args:
        views: Nombre de vues (peut être None)
        
    Returns:
        Chaîne formatée (ex: "1.2M", "500k", "N/A")
        
    Examples:
        >>> format_views(1500000)
        '1.5M'
        >>> format_views(5000)
        '5.0k'
    """
    if not views:
        return "N/A"
    
    try:
        views = int(views)
    except (ValueError, TypeError):
        return str(views)
    
    if views >= 1_000_000:
        return f"{views / 1_000_000:.1f}M"
    elif views >= 1_000:
        return f"{views / 1_000:.1f}k"
    
    return str(views)


# =============================================================================
# FILE OPERATIONS
# =============================================================================

def write_data(output_dir: str, data: str, seg: str) -> None:
    """
    Écrit des données dans un fichier segment.
    
    Args:
        output_dir: Répertoire de sortie
        data: Données à écrire
        seg: Identifiant du segment
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    safe_seg = slugify(str(seg))
    file_path = output_path / f"segment_{safe_seg}.txt"
    
    with file_path.open("w", encoding="utf-8") as f:
        f.write(data)


def load_text(paths: List[str]) -> List[str]:
    """
    Charge le contenu de plusieurs fichiers texte.
    
    Args:
        paths: Liste des chemins de fichiers
        
    Returns:
        Liste des contenus texte
    """
    texts = []
    for path in paths:
        file_path = Path(path)
        with file_path.open("r", encoding="utf-8") as f:
            texts.append(f.read())
    return texts


def clean_files(list_path: List[str]) -> None:
    """
    Nettoie (supprime et recrée) les répertoires spécifiés.
    
    Args:
        list_path: Liste des chemins de répertoires à nettoyer
    """
    for path in list_path:
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path, exist_ok=True)


# =============================================================================
# MARKDOWN UTILITIES
# =============================================================================

# Pattern pour détecter les blocs de code markdown
MARKDOWN_CODE_BLOCK_PATTERN = r"```(?:markdown)?\s*(.*?)\s*```"


def clean_markdown_text(text: str) -> str:
    """
    Nettoie le texte Markdown en supprimant les marqueurs de blocs de code
    et les préambules conversationnels.
    
    Args:
        text: Texte à nettoyer
        
    Returns:
        Texte nettoyé
        
    Examples:
        >>> clean_markdown_text("```markdown\\n# Title\\n```")
        '# Title'
    """
    # Chercher le contenu dans un bloc de code
    match = re.search(MARKDOWN_CODE_BLOCK_PATTERN, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Nettoyage fallback pour les blocs mal formés
    text = text.strip()
    
    if text.startswith("```markdown"):
        text = text.replace("```markdown", "", 1)
    elif text.startswith("```"):
        text = text[3:]
    
    if text.endswith("```"):
        text = text[:-3]
    
    return text.strip()
