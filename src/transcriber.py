import whisper
import os

def transcribe_audio(audio_file: str, device: str = "cpu", model_size: str = "tiny") -> dict:
    model = whisper.load_model(model_size, device=device)
    result = model.transcribe(audio_file)
    # Nettoyage après transcription
    if os.path.exists(audio_file):
        os.remove(audio_file)
    return result

