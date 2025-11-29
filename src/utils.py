import re
import os
from pathlib import Path

def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"\s+", "_", value)
    return value.strip("_")


def write_data(output_dir, data, seg):
    output_dir = Path(output_dir)       
    output_dir.mkdir(parents=True, exist_ok=True) 
    file_path = output_dir / f"segment_{seg}.txt" 
    with file_path.open("w", encoding="utf-8") as file:
        file.write(data)



def load_text(paths):
    text = []
    for path in paths:
        path = Path(path)  
        with path.open("r", encoding="utf-8") as f:
            text.append(f.read())
    return text
