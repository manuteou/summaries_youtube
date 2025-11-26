import os
import asyncio
from moviepy import AudioFileClip
from pydub import AudioSegment
from summarizer import summarize_long_text, enhance_markdown
import whisper
import warnings
warnings.filterwarnings("ignore")
from rich.console import Console
from rich.markdown import Markdown
from exporter import save_summary
from ollama import Client
import multiprocessing as mp

from tqdm import tqdm
import time

from dotenv import load_dotenv
load_dotenv()

DEVICE = os.getenv("DEVICE")
MODEL = os.getenv("MODEL")

whisper_model = None

def init_worker():
    global whisper_model
    whisper_model = whisper.load_model(MODEL, device=DEVICE)


def split_audio_equal(input_file, output_dir, num_segments=10):
    audio = AudioSegment.from_file(input_file)
    duration = len(audio) 
    segment_length = duration // num_segments

    segments = []
    for i in range(num_segments):
        start = i * segment_length
        end = start + segment_length if i < num_segments - 1 else duration
        segment = audio[start:end]
        segment_path = os.path.join(output_dir, f"segment_{i}.mp3")
        segment.export(segment_path, format="mp3")
        segments.append(segment_path)
    return segments


def extract_audio_from_mp4(input_video, output_dir="./test_audio", num_segments=10):
    os.makedirs(output_dir, exist_ok=True)
    audio = AudioFileClip(input_video)
    audio_path = f"{output_dir}/full_audio.mp3"
    audio.write_audiofile(audio_path, codec="mp3", bitrate="80k")
    segments = split_audio_equal(audio_path, output_dir, num_segments=num_segments)
    os.remove(audio_path)
    return segments


def transcribe_audio(audio_file: str) -> str:
    global whisper_model
    result = whisper_model.transcribe(audio_file)
    if os.path.exists(audio_file):
        os.remove(audio_file)
    return result['text']

#def transcribe_audio_from_mp4(segments):
#    text = []
#    for segment in segments:
#        data = transcribe_audio(segment)
#        text.append(data)
#        os.remove(segment)
#    print(data)
#    return data


def transcribe_audio_from_mp4(segments):
    start_time = time.time()  
    results = []

    with mp.Pool(processes=mp.cpu_count(), initializer=init_worker) as pool:
        for result in tqdm(pool.imap(transcribe_audio, segments),
                           total=len(segments),
                           desc="Transcription en cours",
                           unit="segment",
                           dynamic_ncols=True):
            results.append(result)

    elapsed = time.time() - start_time
    print(f"\n✅ Transcription terminée : {len(segments)} segments traités en {elapsed:.2f} secondes")
    print(f"⏱ Temps moyen par segment : {elapsed / len(segments):.2f} s")
    print(f"⚡ Vitesse : {len(segments) / elapsed:.2f} segments/sec")

    return results



if __name__ == "__main__":
    OLLAMA_MODEL="gemma3:4b"
    OLLAMA_HOST="localhost:11434"
    console = Console()
    client = Client(host=OLLAMA_HOST, headers={"x-some-header": "some-value"})
    segments = extract_audio_from_mp4("/home/manu/app/summaries_youtube/src/Réunion Pilotage Direction de campus-20251125_093453-Enregistrement de la réunion.mp4")
    texts = transcribe_audio_from_mp4(segments)
    all_texts = "\n\n".join(texts)
    summary =  summarize_long_text(all_texts, client, OLLAMA_MODEL, author="Laura")
    final_summary = enhance_markdown(summary,client, OLLAMA_MODEL)
    md = Markdown(final_summary)
    console.print(md)
    title = 'test'
    save_summary(final_summary, title, "summaries", "md")
