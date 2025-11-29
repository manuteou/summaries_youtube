from summarizer import Summarizer

class DummyClient:
    def chat(self, model, messages):
        return {"message": {"content": "Résumé factice"}}

def test_summarize_text():
    client = DummyClient()
    summarizer = Summarizer(client, "model")
    result = summarizer.summarize_text("Texte de test", "author")
    assert "Résumé" in result