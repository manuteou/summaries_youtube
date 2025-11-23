import os
from exporter import save_summary

def test_save_markdown(tmp_path):
    summary = "# Titre\n\n- Point 1\n- Point 2"
    title = "Test Video"
    output_file = save_summary(summary, title, tmp_path, "md")
    assert os.path.exists(output_file)
    assert output_file.endswith(".md")

def test_save_html(tmp_path):
    summary = "# Titre\n\n- Point 1\n- Point 2"
    title = "Test Video"
    output_file = save_summary(summary, title, tmp_path, "html")
    assert os.path.exists(output_file)
    assert output_file.endswith(".html")

def test_save_pdf(tmp_path):
    summary = "# Titre\n\n- Point 1\n- Point 2"
    title = "Test Video"
    output_file = save_summary(summary, title, tmp_path, "pdf")
    assert os.path.exists(output_file)
    assert output_file.endswith(".pdf")