from xhtml2pdf import pisa
import os

def create_pdf():
    output_file = "test_toc_position.pdf"
    
    html_content = """
    <html>
    <head>
        <style>
            @page title_template { margin: 2cm; }
            @page toc_template { margin: 2cm; }
            @page content_template { margin: 2cm; }
            
            body { font-family: Helvetica; }
            h1 { color: red; }
            .doc-title { font-size: 24pt; text-align: center; }
        </style>
    </head>
    <body>
        <div class="doc-title">Test Title</div>
        
        <pdf:nexttemplate name="toc_template" />
        <pdf:nextpage />
        
        <div style="background-color: yellow;">
            <h1>Sommaire</h1>
            <pdf:toc />
        </div>
        
        <pdf:nexttemplate name="content_template" />
        <pdf:nextpage />
        
        <h1>Chapter 1</h1>
        <p>Content of chapter 1.</p>
        <pdf:nextpage />
        <h1>Chapter 2</h1>
        <p>Content of chapter 2.</p>
    </body>
    </html>
    """
    
    with open(output_file, "wb") as f:
        pisa.CreatePDF(html_content, dest=f)
    
    print(f"Created {output_file}")

if __name__ == "__main__":
    create_pdf()
