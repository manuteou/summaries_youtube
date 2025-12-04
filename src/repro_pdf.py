import os
from exporter import Exporter

def test_pdf_title():
    exporter = Exporter("./test_output")
    title = "les nouveaux metiers de la tech"
    summary = "# Test Summary\n\nThis is a test summary."
    
    print(f"Testing title: '{title}'")
    exporter.save_summary(summary, title, "pdf", [{"title": "Test Source", "url": "http://example.com", "date": "2023-01-01"}])
    print("PDF generated in ./test_output")

if __name__ == "__main__":
    test_pdf_title()
