import os
import io
from datetime import datetime

import markdown
from xhtml2pdf import pisa
from markdownify import markdownify as md
from utils import slugify, clean_markdown_text
from abc import ABC, abstractmethod

# --- Helper Functions (Shared Logic) ---

def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def is_html(text: str) -> bool:
    """Detects if text is likely HTML."""
    text = text.strip()
    return (
        text.startswith("<") or 
        "<p>" in text or 
        "<div>" in text or 
        "<h1>" in text or 
        "<span" in text
    )

def to_html(content: str) -> str:
    """Converts content to HTML."""
    if is_html(content):
        return content
    else:
        return markdown.markdown(clean_markdown_text(content), extensions=['extra', 'codehilite'])

def to_markdown(content: str) -> str:
    """Converts content to Markdown."""
    if is_html(content):
        return md(content, heading_style="ATX")
    else:
        return clean_markdown_text(content)

def format_sources_md(source_info):
    if not source_info:
        return ""
    sources_text = "\n\n## Sources\n"
    for source in source_info:
        title = source.get("title", "Inconnu")
        url = source.get("url", "#")
        date = source.get("date")
        if date:
            sources_text += f"- [{title} ({date})]({url})\n"
        else:
            sources_text += f"- [{title}]({url})\n"
    return sources_text

def format_sources_html(source_info):
    if not source_info:
        return ""
    html_str = "<hr><h2>Sources</h2><ul>"
    for source in source_info:
        title = source.get("title", "Inconnu")
        url = source.get("url", "#")
        date = source.get("date")
        date_str = f" ({date})" if date else ""
        html_str += f'<li><a href="{url}">{title}{date_str}</a></li>'
    html_str += "</ul>"
    return html_str

def wrap_html(html_body: str, title: str, css_content: str, source_info=None, for_pdf=False) -> str:
    sources_html = format_sources_html(source_info)
    
    # PDF Header includes page numbers
    footer_div = ""
    toc_div = ""
    if for_pdf:
        # Vertical centering for PDF
        title_html = (
            f'<div style="position: absolute; top: 45%; left: 0; width: 100%; text-align: center;">'
            f'<div class="doc-title" style="margin: 0 auto;">{title}</div>'
            f'</div>'
        )
        footer_div = """
        <div id="footerContent">
            Page <pdf:pagenumber /> / <pdf:pagecount />
        </div>
        """
        toc_div = """
        <div id="toc-container">
            <h1>Sommaire</h1>
            <pdf:toc />
        </div>
        <pdf:nextpage />
        """
    else:
        title_html = f'<div class="doc-title">{title}</div>'
        
    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
        @page {{
            size: A4;
            margin: 2cm;
            @frame footer_frame {{
                -pdf-frame-content: footerContent;
                bottom: 1cm;
                margin-left: 2cm;
                margin-right: 2cm;
                height: 1cm;
            }}
        }}
        
        {css_content}
        </style>
    </head>
    <body>
        {title_html}
        <pdf:nextpage />
        
        {toc_div}
        
        <div class="content">
            {html_body}
        </div>
        
        <div id="sources">
            {sources_html}
        </div>
        
        {footer_div}
    </body>
    </html>
    """

# --- Strategies ---

class ExportStrategy(ABC):
    @abstractmethod
    def export(self, summary: str, output_file: str, title: str, source_info=None):
        pass

class MarkdownStrategy(ExportStrategy):
    def export(self, summary: str, output_file: str, title: str, source_info=None):
        content = to_markdown(summary)
        content += format_sources_md(source_info)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)

class TextStrategy(ExportStrategy):
    def export(self, summary: str, output_file: str, title: str, source_info=None):
        content = to_markdown(summary) # Reusing markdown logic as base
        content += format_sources_md(source_info)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)

class HTMLStrategy(ExportStrategy):
    def __init__(self, css_content):
        self.css_content = css_content

    def export(self, summary: str, output_file: str, title: str, source_info=None):
        html_body = to_html(summary)
        full_html = wrap_html(html_body, title, self.css_content, source_info, for_pdf=False)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(full_html)

class PDFStrategy(ExportStrategy):
    def __init__(self, css_content):
        self.css_content = css_content

    def export(self, summary: str, output_file: str, title: str, source_info=None):
        html_body = to_html(summary)
        full_html = wrap_html(html_body, title, self.css_content, source_info, for_pdf=True)
        
        pdf_file = io.BytesIO()
        pisa.CreatePDF(full_html, dest=pdf_file)
        
        with open(output_file, "wb") as f:
            f.write(pdf_file.getvalue())

# --- Context Class ---

class Exporter:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.css_content = load_css()
        
        # Initialize strategies
        self.strategies = {
            "md": MarkdownStrategy(),
            "txt": TextStrategy(),
            "html": HTMLStrategy(self.css_content),
            "pdf": PDFStrategy(self.css_content)
        }

    def save_summary(self, summary: str, title: str, fmt: str, source_info=None):
        if fmt not in self.strategies:
            raise ValueError(f"Format non supporté : {fmt}. Utilisez 'md', 'txt', 'html' ou 'pdf'.")
            
        slug = slugify(title)
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{slug}_{date_str}.{fmt}"
        output_file = os.path.join(self.output_dir, filename)

        self.strategies[fmt].export(summary, output_file, title, source_info)

        return output_file

    def generate_pdf_bytes(self, summary: str, title: str, source_info=None) -> bytes:
        html_body = to_html(summary)
        full_html = wrap_html(html_body, title, self.css_content, source_info, for_pdf=True)
        
        pdf_file = io.BytesIO()
        pisa.CreatePDF(full_html, dest=pdf_file)
        return pdf_file.getvalue()
