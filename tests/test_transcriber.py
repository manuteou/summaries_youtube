from transcriber import transcribe_audio

def test_transcribe_audio(monkeypatch):
    class DummyModel:
        def transcribe(self, audio_file):
            return {"text": "Texte transcrit"}
    monkeypatch.setattr("whisper.load_model", lambda *args, **kwargs: DummyModel())
    result = transcribe_audio("fake_audio.mp3")
    assert result["text"] == "Texte transcrit"