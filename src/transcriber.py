
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
        """
        Extrait le texte d'un fichier SRT en supprimant les index et les timestamps.
        Gère correctement les sous-titres multi-lignes.
        """
        import re
        
        lines = srt_content.splitlines()
        clean_text = []
        
        # Regex pour identifier les timestamps (ex: 00:00:01,000 --> 00:00:04,000)
        timestamp_pattern = re.compile(r'\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}')
        
        for line in lines:
            line = line.strip()
            # Ignorer les lignes vides
            if not line:
                continue
            # Ignorer les lignes qui sont juste des nombres (index de sous-titre)
            if line.isdigit():
                continue
            # Ignorer les lignes de timestamps
            if timestamp_pattern.match(line):
                continue
            # Ignorer les balises HTML potentielles comme <i>, <b>, <font>
            line = re.sub(r'<[^>]+>', '', line)
                
            clean_text.append(line)
            
        return " ".join(clean_text)

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
