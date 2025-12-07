import re
import os
import shutil
from pathlib import Path
from typing import List
from datetime import datetime, timezone

def time_since(date_obj: datetime) -> str:
    """
    Returns a string representing the time elapsed since the given date.
    E.g., "il y a 2 ans", "il y a 3 mois", "il y a 5 jours".
    """
    if not date_obj:
        return "Date inconnue"
    
    # Ensure date_obj is timezone-aware if it's not
    if date_obj.tzinfo is None:
        date_obj = date_obj.replace(tzinfo=timezone.utc)
        
    now = datetime.now(timezone.utc)
    diff = now - date_obj
    
    seconds = diff.total_seconds()
    
    intervals = (
        ('ans', 31536000),  # 60 * 60 * 24 * 365
        ('mois', 2592000),  # 60 * 60 * 24 * 30
        ('semaines', 604800), # 60 * 60 * 24 * 7
        ('jours', 86400),    # 60 * 60 * 24
        ('heures', 3600),    # 60 * 60
        ('minutes', 60),
        ('secondes', 1),
    )
    
    for name, count in intervals:
        value = seconds // count
        if value >= 1:
            return f"il y a {int(value)} {name}"
            
    return "à l'instant"

def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"\s+", "_", value)
    return value.strip("_")

def format_views(views):
    """Formats a view count number into a human-readable string (e.g., 1.2M, 500k)."""
    if not views:
        return "N/A"
    try:
        views = int(views)
    except:
        return str(views)
        
    if views >= 1_000_000:
        return f"{views / 1_000_000:.1f}M"
    elif views >= 1_000:
        return f"{views / 1_000:.1f}k"
    else:
        return str(views)



def write_data(output_dir, data, seg):
    output_dir = Path(output_dir)       
    output_dir.mkdir(parents=True, exist_ok=True) 
    safe_seg = slugify(str(seg))
    file_path = output_dir / f"segment_{safe_seg}.txt" 
    with file_path.open("w", encoding="utf-8") as file:
        file.write(data)



def load_text(paths):
    text = []
    for path in paths:
        path = Path(path)  
        with path.open("r", encoding="utf-8") as f:
            text.append(f.read())
    return text

def clean_files(list_path: List[str]):
    for path in list_path:
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path, exist_ok=True)    

def clean_markdown_text(text: str) -> str:
    """Removes markdown code block markers and conversational preambles."""
    # Pattern to find content inside ```markdown ... ``` or ``` ... ```
    # re.DOTALL makes . match newlines
    pattern = r"```(?:markdown)?\s*(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Fallback cleanup for simple fences if no full block found (e.g. unclosed)
    text = text.strip()
    if text.startswith("```markdown"):
        text = text.replace("```markdown", "", 1)
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()
