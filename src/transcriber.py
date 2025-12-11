
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
        text = result['text']
        
        # Save to debug file
        try:
            # Use only the filename without extension as the ID
            filename = os.path.basename(audio_file)
            name_without_ext = os.path.splitext(filename)[0]
            
            # Directory path - go up one level from src if running from src, or relative to cwd
            # Ideally use absolute path or relative to project root. 
            # Given user request: C:\Users\froge\Documents\vscode\test_whisper\src\segments_text
            debug_dir = os.path.join(os.path.dirname(__file__), "segments_text")
            os.makedirs(debug_dir, exist_ok=True)
            
            debug_file = os.path.join(debug_dir, f"{name_without_ext}.txt")
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(text)
                
            print(f"DEBUG: Transcription saved to {debug_file}")
        except Exception as e:
            print(f"Warning: Could not save debug transcription: {e}")
            
        return text

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
