from exporter import Exporter
import os
import shutil

OUTPUT_DIR = "./test_full_output"

def test_full_export():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    exporter = Exporter(OUTPUT_DIR)
    
    # Case 1: Pure Markdown Input (e.g. from LLM directly)
    title_md = "Test 1 - Markdown Input"
    summary_md = """# Title 1
    This is a **bold** statement.
    - Item A
    - Item B
    
    ```python
    print("Hello")
    ```
    """
    
    # Case 2: HTML Input (e.g. from Quill editor)
    title_html = "Test 2 - HTML Input"
    summary_html = """<h1>Title 2</h1>
    <p>This is a <strong>bold</strong> statement.</p>
    <ul>
        <li>Item A</li>
        <li>Item B</li>
    </ul>
    <pre><code>print("Hello")</code></pre>
    <p>Text with <span style="color: red;">Color</span>.</p>
    """
    
    source_info = [{"title": "Source 1", "url": "http://example.com", "date": "2023-01-01"}]
    
    formats = ["md", "txt", "html", "pdf"]
    
    print("--- Starting Export Tests ---")
    
    for fmt in formats:
        print(f"\nTesting Format: {fmt}")
        
        # Test MD Input
        try:
            f = exporter.save_summary(summary_md, title_md, fmt, source_info)
            print(f"[OK] MD Input -> {fmt}: {f}")
        except Exception as e:
            print(f"[FAIL] MD Input -> {fmt}: {e}")
            
        # Test HTML Input
        try:
            f = exporter.save_summary(summary_html, title_html, fmt, source_info)
            print(f"[OK] HTML Input -> {fmt}: {f}")
        except Exception as e:
            print(f"[FAIL] HTML Input -> {fmt}: {e}")

if __name__ == "__main__":
    test_full_export()
