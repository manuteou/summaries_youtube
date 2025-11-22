import re

def slugify(value: str) -> str:
    """Nettoie le titre pour créer un nom de fichier valide"""
    value = value.lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"\s+", "_", value)
    return value.strip("_")