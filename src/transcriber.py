import whisper
import os

def transcribe_audio(audio_file: str, model_whisper) -> dict:
    model = model_whisper
    result = model.transcribe(f"{audio_file}")
    #if os.path.exists(audio_file):
    #    os.remove(audio_file)
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
