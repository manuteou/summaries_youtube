import whisper
import os
import time


def transcribe_audio(audio_file: str,device:str, model_size:str ) -> dict:
    whisper_model = whisper.load_model(model_size, device=device)
    result = whisper_model.transcribe(f"{audio_file}")
    if os.path.exists(audio_file):
        os.remove(audio_file)
    return result['text']


def extract_subtitles(fichier_srt):
    lignes = fichier_srt.splitlines()
    lignes = [ligne.strip() for ligne in lignes if ligne.strip()]
    i = 0
    text_ligne = []
    for ligne in lignes:
        i+=1
        if i%3==0:
           text_ligne.append(ligne)
    text = " ".join(text_ligne)
  
    return text


def transcribe_audio_from_mp4(segments, model: str, device: str):
    text = []
    start_time = time.time() 
    whisper_model = whisper.load_model(model, device)
    for i,segment in enumerate(segments):
        print(f"traitement du segement {i+1} en cours")
        data = transcribe_audio(segment, whisper_model)
        text.append(data)
        os.remove(rf"{segment}")
    elapsed = time.time() - start_time
    print(f"\n✅ Transcription terminée : {len(segments)} segments traités en {elapsed:.2f} secondes")
    return text