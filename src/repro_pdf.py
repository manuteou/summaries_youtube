import os
from exporter import Exporter

def test_pdf_title():
    exporter = Exporter("./test_output")
    title = "Test Pandas Colors"
    
    # Simulate HTML from Quill editor with specific formatting
    summary = """
    <h1>Le Panda Géant</h1>
    <p>Ceci est un paragraphe normal.</p>
    <p>Voici du texte <span style="color: red;">en rouge qui doit apparaître en rouge</span>.</p>
    <p>Et une liste :</p>
    <ul>
        <li>Item 1</li>
        <li>Item 2</li>
    </ul>
    """
    
    print(f"Testing title: '{title}'")
    exporter.save_summary(summary, title, "pdf", [{"title": "Wikipedia - Panda", "url": "https://fr.wikipedia.org/wiki/Panda_g%C3%A9ant", "date": "2023-01-01"}])
    print("PDF generated in ./test_output")

if __name__ == "__main__":
    test_pdf_title()
