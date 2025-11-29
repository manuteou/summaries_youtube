import os
from datetime import datetime
from utils import slugify
import markdown
import html
from xhtml2pdf import pisa

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
    elif fmt == "pdf":
        # Clean up potential markdown code blocks from LLM output
        clean_summary = summary.strip()
        if clean_summary.startswith("```markdown"):
            clean_summary = clean_summary.replace("```markdown", "", 1)
        if clean_summary.startswith("```"):
            clean_summary = clean_summary.replace("```", "", 1)
        if clean_summary.endswith("```"):
            clean_summary = clean_summary[:-3]
        
        print(f"DEBUG: Summary length: {len(clean_summary)}")
        
        # Convert Markdown to HTML
        html_content = markdown.markdown(clean_summary, extensions=['extra', 'codehilite'])
        
        # Load CSS
        css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
        css_content = ""
        if os.path.exists(css_path):
            with open(css_path, "r", encoding="utf-8") as f:
                css_content = f.read()
        
        # Wrap HTML with style
        full_html = f"""
        <html>
        <head>
            <style>
            {css_content}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        # Generate PDF
        with open(output_file, "wb") as f:
            pisa.CreatePDF(full_html, dest=f)
    else:
        raise ValueError(f"Format non supporté : {fmt}. Utilisez 'md', 'txt' ou 'pdf'.")

    return output_file
