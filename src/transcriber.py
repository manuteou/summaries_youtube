
import whisper
import os
import time

class WhisperTranscriber:
    def __init__(self, model_size: str, device: str):
        self.model_size = model_size
        self.device = device
        self.model = whisper.load_model(model_size, device=device)

    def transcribe_audio(self, audio_file: str) -> str:
        result = self.model.transcribe(audio_file)
        return result['text']

    @staticmethod
    def extract_subtitles(srt_content: str) -> str:
        lignes = [ligne.strip() for ligne in srt_content.splitlines() if ligne.strip()]
        text_ligne = [ligne for i, ligne in enumerate(lignes, start=1) if i % 3 == 0]
        return " ".join(text_ligne)

    def transcribe_segments(self, segments: list[str]) -> list[str]:
        text_results = []
        start_time = time.time()
        for i, segment in enumerate(segments):
            print(f"Traitement du segment {i+1}/{len(segments)} en cours...")
            transcription = self.transcribe_audio(segment)
            text_results.append(transcription)
        elapsed = time.time() - start_time
        print(f"\n✅ Transcription terminée : {len(segments)} segments traités en {elapsed:.2f} secondes")
        return text_results
