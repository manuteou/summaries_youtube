import os
from datetime import datetime
from utils import slugify
import markdown
import html
from xhtml2pdf import pisa

class Exporter:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _format_sources(self, source_info):
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

    def save_md(self, summary: str, output_file: str, source_info=None):
        content = summary + self._format_sources(source_info)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)

    def save_txt(self, summary: str, output_file: str, source_info=None):
        content = summary + self._format_sources(source_info)
        plain_text = content.replace("**", "").replace("#", "").replace("-", "")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(plain_text.strip())

    def save_pdf(self, summary: str, output_file: str, title: str, source_info=None):
        # Clean up potential markdown code blocks from LLM output
        clean_summary = summary.strip()
        if clean_summary.startswith("```markdown"):
            clean_summary = clean_summary.replace("```markdown", "", 1)
        if clean_summary.startswith("```"):
            clean_summary = clean_summary.replace("```", "", 1)
        if clean_summary.endswith("```"):
            clean_summary = clean_summary[:-3]
        
        # Append sources
        clean_summary += self._format_sources(source_info)
        
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
            @page title_template {{
                margin: 2cm;
            }}
            @page toc_template {{
                margin: 2cm;
            }}
            @page content_template {{
                margin: 2cm;
            }}
            
            {css_content}
            </style>
        </head>
        <body>
            <p class="doc-title">{title}</p>
            
            <pdf:nexttemplate name="toc_template" />
            <pdf:nextpage />
            
            <div id="toc-container">
                <h1>Sommaire</h1>
                <pdf:toc />
            </div>
            
            <pdf:nexttemplate name="content_template" />
            <pdf:nextpage />
            
            {html_content}
        </body>
        </html>
        """

        # Generate PDF
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
        else:
            raise ValueError(f"Format non supporté : {fmt}. Utilisez 'md', 'txt' ou 'pdf'.")

        return output_file
