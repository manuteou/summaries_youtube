import re
import os
import shutil
from pathlib import Path
from typing import List

def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"\s+", "_", value)
    return value.strip("_")


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
