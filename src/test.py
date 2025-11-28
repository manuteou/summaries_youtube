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
import time
import  glob
from transcriber import transcribe_audio
from dotenv import load_dotenv
from utils import load_text
load_dotenv()

DEVICE = os.getenv("DEVICE")
MODEL = os.getenv("MODEL")
OLLAMA_HOST = os.getenv("OLLAMA_HOST")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

FFMPEG_DIR = os.getenv("FFMPEG")
os.environ["PATH"] += os.pathsep + FFMPEG_DIR

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


def transcribe_audio_from_mp4(segments):
    text = []
    start_time = time.time() 
    whisper_model = whisper.load_model(MODEL, device=DEVICE)
    for i,segment in enumerate(segments):
        print(f"traitement du segement {i+1} en cours")
        data = transcribe_audio(segment, whisper_model)
        text.append(data)
        os.remove(rf"{segment}")
    elapsed = time.time() - start_time
    print(f"\n✅ Transcription terminée : {len(segments)} segments traités en {elapsed:.2f} secondes")
    return text


if __name__ == "__main__":
    EXTRACT_AUDIO = False
    console = Console()
    client = Client(host=OLLAMA_HOST, headers={"x-some-header": "some-value"})
    video_path = r"C:\Users\froge\Documents\vscode\test_whisper\src\Réunion Pilotage Direction de campus-20251125_093453-Enregistrement de la réunion.mp4"
    save_path = "summaries"
    title = video_path.split("\\")[-1].split(".")[0]
    if EXTRACT_AUDIO:
        segments = extract_audio_from_mp4("/home/manu/app/summaries_youtube/src/Réunion Pilotage Direction de campus-20251125_093453-Enregistrement de la réunion.mp4")
        texts = transcribe_audio_from_mp4(segments)
    else:
        files = glob.glob("./segment_text/*")
        texts = load_text(files)
    summary = "\n\n".join(texts)
    for _ in range(2):
        summary =  summarize_long_text(summary, client, OLLAMA_MODEL, author=title)
    final_summary = enhance_markdown(summary,client, OLLAMA_MODEL)
    md = Markdown(final_summary)
    console.print(md)
    save_summary(final_summary, title, save_path , "md")
