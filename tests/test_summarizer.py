from summarizer import summarize_text

class DummyClient:
    def chat(self, model, messages):
        return {"message": {"content": "Résumé factice"}}

def test_summarize_text():
    client = DummyClient()
    result = summarize_text("Texte de test", client)
    assert "Résumé" in result