import re
import os

def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"\s+", "_", value)
    return value.strip("_")

def write_data(output_dir, data, seg):
    os.makedirs(output_dir, exist_ok=True)
    with open (f"{output_dir}/segment_{seg}.txt", "w") as file:
        file.write(data)

def load_text(output_dir):
    text=[]
    for path in output_dir:
        with open(path, "r") as files:
            text.append(files.read())
    return text