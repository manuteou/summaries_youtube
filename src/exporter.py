import os
from datetime import datetime
from utils import slugify

def save_summary(summary: str, title: str, output_dir: str, fmt: str):
    os.makedirs(output_dir, exist_ok=True)
    slug = slugify(title)
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{slug}_{date_str}.{fmt}"
    output_file = os.path.join(output_dir, filename)

    if fmt == "md":
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(summary)
    elif fmt == "txt":
        plain_text = summary.replace("**", "").replace("#", "").replace("-", "")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(plain_text.strip())
    else:
        raise ValueError(f"Format non supporté : {fmt}. Utilisez 'md' ou 'txt'.")

    return output_file
