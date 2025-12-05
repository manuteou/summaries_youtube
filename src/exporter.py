import os
from datetime import datetime
import html
import markdown
from xhtml2pdf import pisa
from markdownify import markdownify as md
from utils import slugify, clean_markdown_text

class Exporter:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.css_content = self._load_css()
        
    def _load_css(self):
        css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
        if os.path.exists(css_path):
            with open(css_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def _is_html(self, text: str) -> bool:
        """Detects if text is likely HTML."""
        text = text.strip()
        return (
            text.startswith("<") or 
            "<p>" in text or 
            "<div>" in text or 
            "<h1>" in text or 
            "<span" in text
        )

    def _to_html(self, content: str) -> str:
        """Converts content to HTML."""
        if self._is_html(content):
            return content
        else:
            return markdown.markdown(clean_markdown_text(content), extensions=['extra', 'codehilite'])

    def _to_markdown(self, content: str) -> str:
        """Converts content to Markdown."""
        if self._is_html(content):
            return md(content, heading_style="ATX")
        else:
            return clean_markdown_text(content)
            
    def _to_text(self, content: str) -> str:
        """Converts content to Plain Text."""
        return self._to_markdown(content)

    def _format_sources_md(self, source_info):
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

    def _format_sources_html(self, source_info):
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

    def save_md(self, summary: str, output_file: str, source_info=None):
        content = self._to_markdown(summary)
        content += self._format_sources_md(source_info)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)

    def save_txt(self, summary: str, output_file: str, source_info=None):
        content = self._to_text(summary)
        content += self._format_sources_md(source_info)
        # Optional: strip markdown syntax if strictly required, but usually readable enough
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)

    def _wrap_html(self, html_body: str, title: str, source_info=None, for_pdf=False) -> str:
        sources_html = self._format_sources_html(source_info)
        
        # PDF Header includes page numbers
        footer_div = ""
        toc_div = ""
        if for_pdf:
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
            
            {self.css_content}
            </style>
        </head>
        <body>
            <div class="doc-title">{title}</div>
            
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

    def save_html(self, summary: str, output_file: str, title: str, source_info=None):
        html_body = self._to_html(summary)
        full_html = self._wrap_html(html_body, title, source_info, for_pdf=False)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(full_html)

    def save_pdf(self, summary: str, output_file: str, title: str, source_info=None):
        html_body = self._to_html(summary)
        full_html = self._wrap_html(html_body, title, source_info, for_pdf=True)
        with open(output_file, "wb") as f:
            pisa.CreatePDF(full_html, dest=f)

    def save_summary(self, summary: str, title: str, fmt: str, source_info=None):
        slug = slugify(title)
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{slug}_{date_str}.{fmt}"
        output_file = os.path.join(self.output_dir, filename)

        if fmt == "md":
            self.save_md(summary, output_file, source_info)
        elif fmt == "txt":
            self.save_txt(summary, output_file, source_info)
        elif fmt == "pdf":
            self.save_pdf(summary, output_file, title, source_info)
        elif fmt == "html":
            self.save_html(summary, output_file, title, source_info)
        else:
            raise ValueError(f"Format non supporté : {fmt}. Utilisez 'md', 'txt', 'html' ou 'pdf'.")

        return output_file
